from datetime import datetime
from time import time
from pymongo import MongoClient
from minio import Minio, ResponseError
from minio.error import InvalidBucketError, InvalidBucketName, ResponseError, InvalidAccessKeyId, InvalidArgument, InvalidArgumentError, SignatureDoesNotMatch, AccessDenied, NoSuchKey
from subprocess import check_output, run
from instance.minio_config import MINIO_CONFIG
from instance.mongodb_config import MONGODB_CONFIG
import package.admin as cloud_admin
import os 
import datetime
import json
import package.audit as audit

mongo_client = MongoClient(MONGODB_CONFIG["MONGODB_ENDPOINT"])
db = mongo_client['SEHR_Cloud']
users = db['Users']

class Citizen:

    def create_account(self, username, password):
        """ 
        An account in S-EHR Cloud is created. After the account creation, 
        a bucket named after the citizen is created and a policy allowing 
        the citizen to only view this bucket is applied.  
        """
        res = cloud_admin.create_user(username, password)
        return res

    def download_consent(self, consent_type):
        consent_file = consent_type+".json"
        consent_string = open(consent_file, "r")
        consent_string = consent_string.read()
        consent_json = json.loads(consent_string)
        consent_json["dateTime"] = datetime.datetime.today().isoformat()
        return str(consent_json)

    def upload_consent_string(self, encrypted_consent_in_bytes, encrypted_consent_as_stream, encrypted_consent_name, metadata=None):
        # if metadata: 
        res = self.user.put_object(bucket_name=self.get_username(), 
                            object_name=encrypted_consent_name, 
                            data=encrypted_consent_as_stream, 
                            length=len(encrypted_consent_in_bytes), 
                            metadata=metadata)
        if "consent_store" in encrypted_consent_name: 
            print(self.get_username())
            consent_set = cloud_admin.set_consent_to_store_true(self.get_username())
            print(consent_set)
        
        if "consent_share" in encrypted_consent_name: 
            consent_set = cloud_admin.set_consent_to_share_true(self.get_username())
            print(consent_set)
        
        return res
        # else: 
        #     res = self.user.put_object(bucket_name=self.get_username(), 
        #                      object_name=encrypted_hr_file_name, 
        #                      data=encrypted_hr_file_as_stream, 
        #                      length=len(encrypted_hr_file_in_bytes)
        #                      )
        #     return res

    def check_consent_store(self): 
        # print(self.get_username())
        consent_set = cloud_admin.check_consent_to_store_exists(self.get_username())
        return consent_set

    def check_consent_share(self): 
        # print(self.get_username())
        consent_set = cloud_admin.check_consent_to_share_exists(self.get_username())
        return consent_set

    def withdraw_consent_share(self):
        consent_set = cloud_admin.check_consent_to_share_exists(self.get_username())
        print(consent_set['consentShare'])
        if consent_set['consentShare']:
            res = cloud_admin.withdraw_consent_share(self.get_username())
            return res
        else: 
            return {"msg":"User never agreed to share data with HCPs", "status": 400, "consentShare": False}


    def upload_personal_info_string(self, encrypted_personal_info_in_bytes, encrypted_personal_info_as_stream, encrypted_personal_info_name):
        consent_store_is_set = self.check_consent_store()
        print(consent_store_is_set['consent'])
        if consent_store_is_set['consent']: 
            res = self.user.put_object(bucket_name=self.get_username(), 
                            object_name=encrypted_personal_info_name, 
                            data=encrypted_personal_info_as_stream, 
                            length=len(encrypted_personal_info_in_bytes))
            return res
        else: 
            return consent_store_is_set

    def remove_account(self):
        """ 
        This function erases the user's bucket along with the data stored in it 
        and deletes the account of the user. 
        :returns: a boolean response, whether the account is deleted or not.
        """
        print(self.get_username())
        delete_account = cloud_admin.remove_user(self.get_username())
        print(delete_account)
        # return {'response': delete_account}

    def set_username(self, username):
        self.username = username

    def set_password(self, password):
        self.password = password
    
    def get_username(self):
        return self.username

    def get_password(self):
        return self.password

    def set_user(self):
        try:
            self.user = Minio(MINIO_CONFIG['MINIO_ENDPOINT'], 
                                    access_key=self.username, 
                                    secret_key=self.password, 
                                    secure=MINIO_CONFIG['MINIO_SECURE'])
            self.user.list_buckets()
            return {"msg":"User is now logged in", "status": "OK"}
        except SignatureDoesNotMatch as err: 
            return {"msg": err.message, "status":"F"}
        except ResponseError as err: 
            return {'msg': err.message, 'status': "F"}
        except InvalidAccessKeyId as err: 
            return {"msg": err.message, "status":"F"}
        except InvalidArgument as err: 
            return {"msg": err.message, "status":"F"}
        except InvalidArgumentError as err: 
            return {"msg": err.message, "status":"F"}

    def login(self, username, password):
        try: 
            self.user = Minio(MINIO_CONFIG['MINIO_ENDPOINT'], 
                                    access_key=username, 
                                    secret_key=password, 
                                    secure=MINIO_CONFIG['MINIO_SECURE'])
            self.user.list_buckets()
            self.set_username(username)
            consent_store = self.check_consent_store()
            consent_share = self.check_consent_share()
            return {"msg":"User is now logged in","status":"OK", "consent_store": consent_store["consentStore"], "consent_share": consent_share["consentShare"]}
        except ResponseError as err: 
            return {"msg": err.message, "status": "F"}
        except SignatureDoesNotMatch as err: 
            return {"msg": err.message, "status":"F"}
        except InvalidAccessKeyId as err: 
            return {"msg": err.message, "status":"F"}
        except InvalidArgument as err: 
            return {"msg": err.message, "status":"F"}
        except InvalidArgumentError as err: 
            return {"msg": err.message, "status":"F"}

    def list_objects(self, bucket):
        try:
            objects = self.user.list_objects(bucket_name=bucket)
            objects_dictionary = {}
            for i,object in enumerate(objects):
                if object.object_name == "consent_store.json" or object.object_name == "consent_share.json":
                    continue
                else:
                    object_name = object.object_name
                    object_name = object_name.split('.', 1)[0]
                    objects_dictionary[i] = object_name 
            
            return objects_dictionary
        except AttributeError: 
            return {"err": "User is not logged in"}
        except AccessDenied: 
            return {"err": "Access Denied"}
        except InvalidBucketError as err: 
            return {'err': err.message}
        except InvalidBucketName as err: 
            return {'err': err.message}

    def list_buckets(self):
        try:
            return self.user.list_buckets()
        except AttributeError: 
            return {"err": "User is not logged in"}
        except AccessDenied: 
            return {"err": "Access Denied"}

    def download_audit_info(self):
        res = audit.get_audit_info(self.get_username())
        return res


    def upload_ips(self, encrypted_ips, encrypted_ips_name, metadata=None):
        if metadata: 
            res = self.user.put_object(bucket_name=self.get_username(), 
                             object_name=encrypted_ips_name, 
                             data=encrypted_ips, 
                             length=os.fstat(encrypted_ips.fileno()).st_size, 
                             metadata=metadata)
            return res
        else: 
            res = self.user.put_object(bucket_name=self.get_username(), 
                             object_name=encrypted_ips_name, 
                             data=encrypted_ips, 
                             length=os.fstat(encrypted_ips.fileno()).st_size
                             )
            return res

    def upload_ips_string(self, encrypted_ips_in_bytes, encrypted_ips_as_stream, encrypted_ips_name, metadata=None):
        if metadata: 
            res = self.user.put_object(bucket_name=self.get_username(), 
                             object_name=encrypted_ips_name, 
                             data=encrypted_ips_as_stream, 
                             length=len(encrypted_ips_in_bytes), 
                             metadata=metadata)
            return res
        else: 
            res = self.user.put_object(bucket_name=self.get_username(), 
                             object_name=encrypted_ips_name, 
                             data=encrypted_ips_as_stream, 
                             length=len(encrypted_ips_in_bytes),  
                             )
            return res

    def upload_lr_string(self, encrypted_lr_in_bytes, encrypted_lr_as_stream, encrypted_lr_name, metadata=None):
        if metadata: 
            res = self.user.put_object(bucket_name=self.get_username(), 
                             object_name=encrypted_lr_name, 
                             data=encrypted_lr_as_stream, 
                             length=len(encrypted_lr_in_bytes), 
                             metadata=metadata)
            return res
        else: 
            res = self.user.put_object(bucket_name=self.get_username(), 
                             object_name=encrypted_lr_name, 
                             data=encrypted_lr_as_stream, 
                             length=len(encrypted_lr_in_bytes)
                             )
            return res

    def upload_prescription_string(self, encrypted_prescription_in_bytes, encrypted_prescription_as_stream, encrypted_prescription_name, metadata=None):
        if metadata: 
            res = self.user.put_object(bucket_name=self.get_username(), 
                             object_name=encrypted_prescription_name, 
                             data=encrypted_prescription_as_stream, 
                             length=len(encrypted_prescription_in_bytes), 
                             metadata=metadata)
            return res
        else: 
            res = self.user.put_object(bucket_name=self.get_username(), 
                             object_name=encrypted_prescription_name, 
                             data=encrypted_prescription_as_stream, 
                             length=len(encrypted_prescription_in_bytes)
                             )
            return res

    def upload_hr_file_string(self, encrypted_hr_file_in_bytes, encrypted_hr_file_as_stream, encrypted_hr_file_name, metadata=None):

        consent_store_is_set = self.check_consent_store()
        print(consent_store_is_set['consentStore'])
        if consent_store_is_set['consentStore']: 
            if metadata: 
                res = self.user.put_object(bucket_name=self.get_username(), 
                                object_name=encrypted_hr_file_name, 
                                data=encrypted_hr_file_as_stream, 
                                length=len(encrypted_hr_file_in_bytes), 
                                metadata=metadata)
                res = {'consentStore': True, 'msg': res}
                audit.audit_user_upload_file(self.get_username(), encrypted_hr_file_name)
                return res
            else: 
                res = self.user.put_object(bucket_name=self.get_username(), 
                                object_name=encrypted_hr_file_name, 
                                data=encrypted_hr_file_as_stream, 
                                length=len(encrypted_hr_file_in_bytes)
                                )
                audit.audit_user_upload_file(self.get_username(), encrypted_hr_file_name)
                return res
        else: 
            return consent_store_is_set

    def upload_hr(self, encrypted_hr, encrypted_hr_name, metadata=None):
        if metadata: 
            res = self.user.put_object(bucket_name=self.get_username(), 
                             object_name=encrypted_hr_name, 
                             data=encrypted_hr, 
                             length=os.fstat(encrypted_hr.fileno()).st_size, 
                             metadata=metadata)
            
            audit.audit_user_upload_file(self.get_username(), encrypted_hr_name)
            return res
        else: 
            res = self.user.put_object(bucket_name=self.get_username(), 
                             object_name=encrypted_hr_name, 
                             data=encrypted_hr, 
                             length=os.fstat(encrypted_hr.fileno()).st_size
                             )
            audit.audit_user_upload_file(self.get_username(), encrypted_hr_name)
            return res

    def upload_medical_image(self, encrypted_medical_image, metadata=None):
        pass
    
    def stat_object(self, bucket_name, encrypted_object_name): 
        print(bucket_name)
        try: 
            res = self.user.stat_object(bucket_name=bucket_name, 
                                    object_name=encrypted_object_name)
            
            return {'metadata': res, 'status': 'OK'}
        except NoSuchKey as err: 
            return {'msg': err.message, 'status': 'F'}
        except AccessDenied as err: 
            return {'msg': err.message, 'status': 'F'}
        except InvalidBucketError as err: 
            return {'error': err.message, 'status': 'F'}
        except InvalidBucketName as err: 
            return {'error': err.message, 'status': 'F'}

    def download_ips(self):
        try: 
            encrypted_ips = self.user.get_object(bucket_name=self.get_username(), 
                                object_name='IPS/ips.txt')
            return encrypted_ips.read()
        except ResponseError as err: 
            return {'error': err}
        except NoSuchKey as err: 
            return {'error': err}

    def download_lr(self):
        try: 
            encrypted_lr = self.user.get_object(bucket_name=self.get_username(), 
                                object_name='LR/lr.txt')
            return encrypted_lr.read()
        except ResponseError as err: 
            return {'error': err}
        except NoSuchKey as err: 
            return {'error': err}

    def download_prescription(self):
        try: 
            encrypted_prescription = self.user.get_object(bucket_name=self.get_username(), 
                                object_name='Prescription/prescription.txt')
            return encrypted_prescription.read()
        except ResponseError as err: 
            return {'error': err}
        except NoSuchKey as err: 
            return {'error': err}

    def download_hr_file(self, bucket, object): 
        try: 
            encrypted_hr_file = self.user.get_object(bucket_name=bucket, 
                                object_name=object)
            audit.audit_user_download_file(self.get_username(), object)
            return encrypted_hr_file.read()
        except ResponseError as err: 
            return {'error': err.message}
        except NoSuchKey as err: 
            return {'error': err.message}
        except AccessDenied as err: 
            return {'error': err.message}
        except InvalidBucketError as err: 
            return {'error': err.message}
        except InvalidBucketName as err: 
            return {'error': err.message}

    def download_medical_image(self, encrypted_medical_image_name):
        pass

