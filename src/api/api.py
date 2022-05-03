from flask import Flask, g, request, url_for, redirect, jsonify, render_template, make_response, Response
import os

from minio.error import MetadataTooLarge 
from package.user import Citizen
from package.hcp import HCP
from functools import wraps 
import jwt
from flask_jwt import JWT, jwt_required, current_identity
from werkzeug.exceptions import BadRequestKeyError
import datetime
import json 
import io
import re

app = Flask(__name__)
app.config['SECRET_KEY'] = 'SECRET_KEY'

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.args.get('token')
        if not token: 
            return jsonify({'msg': 'Token is missing or invalid!', 'errorCode' : 403}), 403
        try: 
            data = jwt.decode(token, app.config['SECRET_KEY'])
        except:
            return jsonify({'msg': 'Token is missing or invalid!', 'errorCode' : 403}), 403
        
        return f(*args, **kwargs)
    return decorated

def auth_token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token: 
            return jsonify({'msg': 'Token is missing or invalid!', 'errorCode' : 403}), 403
        try: 
            data = jwt.decode(token, app.config['SECRET_KEY'])
        except:
            return jsonify({'msg': 'Token is missing or invalid!', 'errorCode' : 403}), 403
        
        return f(*args, **kwargs)
    return decorated



user = Citizen()
hcp = HCP() 

def decode_token(token): 
    payload = jwt.decode(token, app.config['SECRET_KEY'])
    return payload

def set_user(token):
    decoded = decode_token(token)
    user.set_username(decoded['username'])
    user.set_password(decoded['password'])
    res = user.set_user()
    return res

def set_hcp(token):
    decoded = decode_token(token)
    citizen_username = decoded['username']
    citizen_username = citizen_username.split('emergency', 1)[0]
    hcp.set_citizen_username(citizen_username)
    hcp.set_hospital(decoded['hospital'])
    hcp.set_hcp_username()
    hcp.set_password()
    res =  hcp.set_hcp()
    return res

def consent_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.args.get('token')
        if not token: 
            return jsonify({'msg': 'Token is missing or invalid!', 'errorCode' : 403}), 403
        try: 
            data = jwt.decode(token, app.config['SECRET_KEY'])
            set_user(token)
            user.check_consent()
        except:
            return jsonify({'msg': 'Token is missing or invalid!', 'errorCode' : 403}), 403

# Citizen API
    """ All the functionalities a Citizen can perform with the S-EHR Cloud. 
    These include: 
        - registration to the S-EHR Cloud through the /citizen/register endpoint
        - login to the S-EHR Cloud through the /citizen/login endpoint
        - remove account from the S-EHR Cloud through the /citizen/remove-account endpoint
        - Upload Encrypted HR data: 
            - upload encrypted IPS to the S-EHR Cloud through the /citizen/upload/ips endpoint
        - Download Encrypted EHR data: 
            - download encrypted IPS from the S-EHR Cloud through the /citizen/download/ips
    """

@app.route("/citizen/register", methods=['POST', 'GET'])
def register():
    username = request.args.get('username')
    password = request.args.get('password')
    if username and password: 
        res = user.create_account(username, password)
        return res, 200
    else: 
        return jsonify({'msg': 'username or password is missing', 'errorCode' : 403}), 403

# Download consent to store data from the S-EHR Cloud
@app.route('/citizen/consent/download/store', methods=['GET'])
@token_required
def download_consent_store():
    token = request.args.get('token')
    set_user(token)

    consent = user.download_consent(consent_type="consent_store") 
    return Response( 
        consent, 
        # mimetype='text/plain', 
        headers={"Content-Disposition": "attachment;filename=consent_store.json"} 
    )

# Download consent to share data with authorized HCPs during an emergency from the S-EHR Cloud
@app.route('/citizen/consent/download/share', methods=['GET'])
@token_required
def download_consent_share():
    token = request.args.get('token')
    set_user(token)

    consent = user.download_consent(consent_type="consent_share") 
    return Response( 
        consent, 
        # mimetype='text/plain', 
        headers={"Content-Disposition": "attachment;filename=consent_share.json"} 
    )

@app.route("/citizen/consent/upload/store", methods=['POST'])
@token_required
def upload_consent_store():
    token = request.args.get('token')
    res = set_user(token)
    if res['status'] == 'OK':        
        if request.method == 'POST':
            try:
                if 'consent_store' in request.form:
                    consent_store = request.form['consent_store']
                    encrypted_consent_store = "consent_store.json"
                    consent_store_byte = consent_store.encode('utf-8')
                    consent_store_stream = io.BytesIO(consent_store_byte)

                    res = user.upload_consent_string(encrypted_consent_as_stream=consent_store_stream,
                                                encrypted_consent_in_bytes=consent_store_byte,
                                                encrypted_consent_name=encrypted_consent_store)
                    return {'msg': res, 'name': encrypted_consent_store}, 200
                else: 
                    return {'msg': 'please select consent (to store data) to upload', 'errorCode' : 400}, 400
            except BadRequestKeyError as err: 
                return {'msg': 'No file is included', 'error': err, 'errorCode' : 400}, 400
    else: 
        return {'msg': 'Token is missing or invalid', 'errorCode' : 403}, 403
    return '''
    <!doctype html>
    <title>stream_upload</title>
    <h1>stream_upload</h1>
    <form method=post enctype=multipart/form-data>
    <input type="text" name="consent_store" id="consent_store">
    <input type=submit value=Text>
    </form>
    '''

@app.route("/citizen/consent/upload/share", methods=['POST'])
@token_required
def upload_consent_share():
    token = request.args.get('token')
    res = set_user(token)
    if res['status'] == 'OK':        
        if request.method == 'POST':
            try:
                if 'consent_share' in request.form:
                    consent_share = request.form['consent_share']
                    encrypted_consent_share = "consent_share.json"
                    consent_share_byte = consent_share.encode('utf-8')
                    consent_share_stream = io.BytesIO(consent_share_byte)

                    res = user.upload_consent_string(encrypted_consent_as_stream=consent_share_stream,
                                                encrypted_consent_in_bytes=consent_share_byte,
                                                encrypted_consent_name=encrypted_consent_share)
                    emergency_token = jwt.encode({'username': user.get_username(), 'exp': datetime.datetime.utcnow()+datetime.timedelta(minutes=2000000)}, app.config['SECRET_KEY'])
                    return {'msg': res, 'name': encrypted_consent_share, 'emergency_token': emergency_token.decode('UTF-8')}, 200
                else: 
                    return {'msg': 'please select consent (to share data) to upload', 'errorCode' : 400}, 400
            except BadRequestKeyError as err: 
                return {'msg': 'No file is included', 'error': err, 'errorCode' : 400}, 400
    else: 
        return {'msg': 'Token is missing or invalid', 'errorCode' : 403}, 403
    return '''
    <!doctype html>
    <title>stream_upload</title>
    <h1>stream_upload</h1>
    <form method=post enctype=multipart/form-data>
    <input type="text" name="consent_share" id="consent_share">
    <input type=submit value=Text>
    </form>
    '''

@app.route('/citizen/consent/download/shareisset', methods=['GET'])
@token_required
def check_consent_share():
    token = request.args.get('token')
    set_user(token)

    consent = user.check_consent_share()
    return consent

@app.route('/citizen/consent/download/storeisset', methods=['GET'])
@token_required
def check_consent_store():
    token = request.args.get('token')
    set_user(token)

    consent = user.check_consent_store()
    return consent

@app.route('/citizen/consent/withdraw/share', methods=['POST'])
@token_required
def withdraw_consent():
    token = request.args.get('token')
    set_user(token)

    res = user.withdraw_consent_share()
    return res

@app.route("/citizen/login", methods=['GET', 'POST'])
def login(username='', password=''):
    username = request.args.get('username')
    password = request.args.get('password')
    if username and password: 
        response = user.login(username, password)
        print(response)
        if response['status'] == 'OK':
            auth = request.authorization
            token = jwt.encode({'username': username, 
                                'password':password, 
                                'exp': datetime.datetime.utcnow()+datetime.timedelta(minutes=2000000)}, 
                                app.config['SECRET_KEY'])

            consent_share_is_set = user.check_consent_share()
            if consent_share_is_set['consentShare']: 
                emergency_token = jwt.encode({'username': username, 'exp': datetime.datetime.utcnow()+datetime.timedelta(minutes=2000000)}, app.config['SECRET_KEY'])
                return jsonify({'token': token.decode('UTF-8'), 
                                'emergency_token': emergency_token.decode('UTF-8'), 
                                'consentStoreIsAccepted': str(response['consent_store']), 
                                'consentShareIsAccepted': str(response['consent_share'])}), 200

            return jsonify({'token': token.decode('UTF-8'), 
                            'consentStoreIsAccepted': str(response['consent_store']), 
                            'consentShareIsAccepted': str(response['consent_share'])}), 200
        else: 
            return jsonify({'msg': 'username or password is missing or wrong', 'errorCode' : 403}), 403
    else: 
        return jsonify({'msg': 'username or password is missing', 'errorCode' : 403}), 403

# Upload encrypted Personal Info including name, and citizen's photo
@app.route('/citizen/upload/personalinfo', methods=['GET', 'POST'])
@token_required
def upload_personal_info_string():
    token = request.args.get('token')
    res = set_user(token)
    if res['status'] == 'OK':
        if request.method == 'POST':
            try:
                if 'personal_info' in request.form:
                    personal_info = request.form['personal_info']
                    encrypted_personal_info_name = 'personal_info.json'
                    personal_info_byte = personal_info.encode('utf-8')
                    personal_info_stream = io.BytesIO(personal_info_byte)

                    res = user.upload_personal_info_string(encrypted_personal_info_as_stream=personal_info_stream,
                                                encrypted_personal_info_in_bytes=personal_info_byte,
                                                encrypted_personal_info_name=encrypted_personal_info_name)
                    return {'msg': res, 'name': encrypted_personal_info_name}
                else: 
                    return {'msg': 'please select your peronsal info to upload', 'errorCode' : 400}
            except BadRequestKeyError as err: 
                return {'msg': 'no file is included', 'error': err, 'errorCode' : 400}
    else: 
        return {'msg': 'Token is missing or invalid', 'errorCode' : 403}
    return '''
    <!doctype html>
    <title>stream_upload</title>
    <h1>stream_upload</h1>
    <form method=post enctype=multipart/form-data>
    <input type="text" name="personal_info" id="personal_info">
    <input type=submit value=Text>
    </form>
    '''

@app.route("/citizen/removeaccount", methods=['GET', 'POST'])
@token_required
def remove_account():
    token = request.args.get('token')
    res = set_user(token)
    
    if res['status'] == 'OK':
        
        res = user.remove_account()
        return {'msg': 'The account is deleted and the data included is also dropped'}, 200
        # return res
    else: 
        return {'msg': 'something went wrong', 'errorCode': 400}, 400

@app.route('/citizen/buckets')
@token_required
def list_buckets():
    token = request.args.get('token')
    res = set_user(token)
    if res['status'] == 'OK':
        res = user.list_buckets()
        outp = []
        for bucket in res:
            outp.append(bucket.name)
        return jsonify({"buckets": outp})
    else: 
        return {'msg': 'token is missing or invalid', 'errorCode' : 403}

@app.route('/citizen/buckets/<bucket>')
@token_required
def list_objects(bucket):
    token = request.args.get('token')
    res = set_user(token)
    bucket = request.view_args['bucket']
    # if 'bucket' in request.args:
    #     bucket = request.args.get('bucket')
    # else: 
    #     bucket = user.get_username()

    res = set_user(token)
    if res['status'] == 'OK':
        res = user.list_objects(bucket)
        print(type(res))
        return res
        
    else: 
        return {'msg': 'token is missing or invalid', 'errorCode' : 403}

# Upload encrypted HR File without specifying data type
@app.route('/citizen/upload/hr', methods=['GET', 'POST'])
@token_required
def upload_hr_string():
    token = request.args.get('token')
    res = set_user(token)
    if res['status'] == 'OK':
        if 'metadata' in request.args:
            metadata = request.args.get('metadata')
            metadata = json.loads(metadata)
            if "hr-type" not in metadata: 
                return {'msg': 'HR type is not included in the metadata', 'errorCode' : 400}, 400
            if "file-type" not in metadata: 
                return {'msg': 'File type is not included in the metadata', 'errorCode' : 400}, 400
        else: 
            return {'msg': 'metadata is missing', 'errorCode' : 400}, 400
        
        if request.method == 'POST':
            try:
                if 'hr_file' in request.form:
                    hr_file = request.form['hr_file']
                    encrypted_hr_file_name = metadata['hr-type']+"."+metadata['file-type']
                    hr_file_byte = hr_file.encode('utf-8')
                    hr_file_stream = io.BytesIO(hr_file_byte)

                    res = user.upload_hr_file_string(encrypted_hr_file_as_stream=hr_file_stream,
                                                encrypted_hr_file_in_bytes=hr_file_byte,
                                                encrypted_hr_file_name=encrypted_hr_file_name, 
                                                metadata=metadata)
                    

                else: 
                    return {'msg': 'please select HR file to upload', 'errorCode' : 400}, 400
            except BadRequestKeyError as err: 
                return {'msg': 'No file is included', 'error': err, 'errorCode' : 400}, 400
    else: 
        return {'msg': 'Token is missing or invalid', 'errorCode' : 403}, 403
    return '''
    <!doctype html>
    <title>stream_upload</title>
    <h1>stream_upload</h1>
    <form method=post enctype=multipart/form-data>
    <input type="text" name="hr_file" id="hr_file">
    <input type=submit value=Text>
    </form>
    '''

# TODO This will be used to download the metadata of an object
@app.route('/citizen/<bucket>/<object>/metadata', methods=['GET'])
@token_required
def stat_object(bucket, object):
    """
    A functionality that given the hr and file type returns the metadata of the object

    Returns:
        json:   a json object containing the metadata that are stored alongside 
                the object in the MinIO server
                
                If the object is not found in the server, a relevant message in the form
                of json object appears
    """
    
    token = request.args.get('token')
    set_user(token)
    bucket = request.view_args['bucket']
    object = request.view_args['object']

    res = user.stat_object(bucket, object)

    if res['status'] == 'OK':

            # return {res['res'].metadata}
        return {'metadata': [res['metadata'].metadata], 'size': res['metadata'].size}
    else: 
        return res


# Download encrypted HR file from the S-EHR Cloud
@app.route('/citizen/<bucket>/<object>', methods=['GET'])
@token_required
def download_hr(bucket, object):
    token = request.args.get('token')
    res = set_user(token)

    if res['status'] == 'OK':
        bucket = request.view_args['bucket']
        object = request.view_args['object']

    is_consent_store = user.check_consent_store()

    if is_consent_store['consentStore']:
        hr_file = user.download_hr_file(bucket, object) 

        if isinstance(hr_file, dict): 
            return {'msg': hr_file['error'], 'errorCode':400}, 400
        return Response( 
            hr_file, 
            # mimetype='text/plain', 
            headers={"Content-Disposition": "attachment;filename=hr_file.txt"} 
        ), 200
    else: 
        return is_consent_store

@app.route('/citizen/auditing')
def audit_info():
    token = request.args.get('token')
    res = set_user(token)
    if res['status'] == 'OK':
        audit_info = user.download_audit_info()
        return audit_info


#####################################################################
#####################################################################
#####################################################################
#####################################################################
#####################################################################
# HCP API
    """ All the functionalities an HCP  can perform during an emergency with the S-EHR Cloud. 
    These include: 
        - download of Citizen's IPS from the S-EHR Cloud
        - download of the Citizen's entire HR from the S-EHR Cloud
        - download of the Citizen's Medical Images from the S-EHR Cloud
        - upload modified IPS (with new entries) to the S-EHR Cloud
        - upload modified HR (with new entries) to the S-EHR Cloud
        - upload of a new Medical Image to the S-EHR Cloud
    
    These functionalities can only be operated when the HCP is authorized by the Certification Authority
    """

@app.route('/hcp/requestaccess', methods=['POST'])
@auth_token_required
def register_hcp():
    citizen_token = request.headers.get('Authorization')
    hcp_name = request.headers.get('hcp_name')
    # if 'token' in request.args:
    #     citizen_token = request.args.get('token')
    payload = decode_token(citizen_token)
    citizen_username = payload['username']

    # else: 
    #     return {'msg': 'token is missing or invalid', 'status': 409}
    
    if 'HCO-attrs' in request.headers:
        hospital = request.headers.get('HCO-attrs')
    else: 
        return {'msg': 'Hospital identification info is missing from headers', 'status': 409}

    if 'HCO-certificate' in request.headers:
        certificate = request.headers.get('HCO-certificate')
    else: 
        return {'msg': 'Hospital identification info is missing from headers', 'status': 409}
    # Request to evaluate hospital attributes to the ABAC engine
    attr_evaluation = True

    if attr_evaluation:
        res = hcp.create_hcp_account(citizen_username, hospital, hcp_name, certificate)
        print(res['status'])
        if res['status'] == 200:
            token = jwt.encode({'username': hcp.get_hcp_username(), 
                                'password':hcp.get_password(), 
                                'citizen': hcp.get_citizen_username(),
                                'hospital': hcp.get_hospital(),
                                'exp': datetime.datetime.utcnow()+datetime.timedelta(minutes=2000000)}, 
                                app.config['SECRET_KEY'])
            
            return jsonify({'token': token.decode('UTF-8'), 'status':200, 'msg': 'HCP account is created'})
        elif (res['status'] == 403):
            return res
        else: 
            token = jwt.encode({'username': hcp.get_hcp_username(), 
                                'password':hcp.get_password(), 
                                'citizen': hcp.get_citizen_username(),
                                'hospital': hcp.get_hospital(),
                                'exp': datetime.datetime.utcnow()+datetime.timedelta(minutes=2000000)}, 
                                app.config['SECRET_KEY'])

            res['token'] = token.decode('UTF-8')
            return jsonify(res)
    else:
        return jsonify({'msg': 'Hospital attributes were not accepted', 'status': 409})

@app.route('/hcp/<bucket>/<object>', methods=['GET'])
@auth_token_required
def hcp_download_hr(bucket, object):
    token = request.headers.get('Authorization')
    hcp_name = request.headers.get('hcp_name')
    decoded = decode_token(token)

    res = set_hcp(token)
    print(hcp.get_hcp_username())
    # return hcp.get_hcp_username()

    if res['status'] == 'OK':
        bucket = request.view_args['bucket']
        object = request.view_args['object']

    hr_file = hcp.download_hr_file(bucket, object, hcp_name) 

    if isinstance(hr_file, dict): 
        return {'msg': hr_file['err'], 'errorCode':400}, 400
    return Response( 
            hr_file, 
            # mimetype='text/plain', 
            headers={"Content-Disposition": "attachment;filename=hr_file.txt"} 
        ), 200

# HCP uploads encrypted HR File without specifying data type
@app.route('/hcp/upload/hr', methods=['GET', 'POST'])
@auth_token_required
def hcp_upload_hr_string():
    token = request.headers.get('Authorization')
    hcp_name = request.headers.get('hcp_name')
    res = set_hcp(token)
    if res['status'] == 'OK':
        if 'metadata' in request.args:
            metadata = request.args.get('metadata')
            metadata = json.loads(metadata)
            if "hr-type" not in metadata: 
                return {'msg': 'HR type is not included in the metadata', 'errorCode' : 400}, 400
            if "file-type" not in metadata: 
                return {'msg': 'File type is not included in the metadata', 'errorCode' : 400}, 400
        else: 
            return {'msg': 'metadata is missing', 'errorCode' : 400}, 400
        
        if request.method == 'POST':
            try:
                if 'hr_file' in request.form:
                    hr_file = request.form['hr_file']
                    encrypted_hr_file_name = metadata['hr-type']+"."+metadata['file-type']
                    hr_file_byte = hr_file.encode('utf-8')
                    hr_file_stream = io.BytesIO(hr_file_byte)

                    res = hcp.upload_hr_file_string(encrypted_hr_file_as_stream=hr_file_stream,
                                                encrypted_hr_file_in_bytes=hr_file_byte,
                                                encrypted_hr_file_name=encrypted_hr_file_name, 
                                                metadata=metadata, 
                                                hcp_name=hcp_name)

                else: 
                    return {'msg': 'please select HR file to upload', 'errorCode' : 400}, 400
            except BadRequestKeyError as err: 
                return {'msg': 'No file is included', 'error': err, 'errorCode' : 400}, 400
    else: 
        return {'msg': 'Token is missing or invalid', 'errorCode' : 403}, 403
    return '''
    <!doctype html>
    <title>stream_upload</title>
    <h1>stream_upload</h1>
    <form method=post enctype=multipart/form-data>
    <input type="text" name="hr_file" id="hr_file">
    <input type=submit value=Text>
    </form>
    '''

@app.route('/hcp/buckets/<bucket>', methods=['GET'])
@auth_token_required
def list_objects_hcp(bucket):
    token = request.headers.get('Authorization')
    res = set_hcp(token)

    bucket = request.view_args['bucket']

    # if 'bucket' in request.args:
    #     bucket = request.args.get('bucket')
    # else: 
    #     bucket = hcp.get_citizen_username()
    
    print(bucket)
    if res['status'] == 'OK':
        objects_dictionaty = hcp.list_objects(bucket)
        return objects_dictionaty
    else: 
        return {'msg':'something went wrong', 'errorCode':400}

@app.route('/hcp/buckets', methods=['GET'])
@auth_token_required
def list_buckets_hcp():
    token = request.headers.get('Authorization')
    res = set_hcp(token)
    if res['status'] == 'OK':
        res = hcp.list_buckets()
        outp = []
        for bucket in res:
            outp.append(bucket.name)
        return jsonify({"buckets": outp})
    else: 
        return {'msg': 'token is missing or invalid', 'errorCode' : 403}

@app.route('/hcp/<bucket>/<object>/metadata', methods=['GET'])
@auth_token_required
def hcp_stat_object(bucket, object):
    """
    A functionality that given the hr and file type returns the metadata of the object

    Returns:
        json:   a json object containing the metadata that are stored alongside 
                the object in the MinIO server
                
                If the object is not found in the server, a relevant message in the form
                of json object appears
    """
    
    token = request.headers.get('Authorization')
    set_hcp(token)
    bucket = request.view_args['bucket']
    object = request.view_args['object']

    res = hcp.stat_object(bucket, object)

    if res['status'] == 'OK':

            # return {res['res'].metadata}
        return {'metadata': [res['metadata'].metadata], 'size': res['metadata'].size}
    else: 
        return res

# Run Flask App
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
