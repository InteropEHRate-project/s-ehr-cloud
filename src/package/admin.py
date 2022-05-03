from pymongo import MongoClient
from minio import Minio, ResponseError 
from minio.error import BucketAlreadyExists, BucketAlreadyOwnedByYou
from subprocess import check_output, run
from instance.minio_config import MINIO_CONFIG
from instance.mongodb_config import MONGODB_CONFIG
from instance.enc_config import ENC
import os 
import datetime
from fernet import Fernet
import json

mongo_client = MongoClient(MONGODB_CONFIG["MONGODB_ENDPOINT"])
db = mongo_client['SEHR_Cloud']
users = db['Users']
hcps = db['HCP']

admin_user = Minio(MINIO_CONFIG['MINIO_ENDPOINT'], 
                    access_key=MINIO_CONFIG['MINIO_ACCESS_KEY'],
                    secret_key=MINIO_CONFIG['MINIO_SECRET_KEY'],
                    secure=MINIO_CONFIG['MINIO_SECURE'])

def create_user(username, password):
    if users.find({"username":username}).count() == 0:
        add_user_command = "./mc admin user add iehr "+username+" "+password
        add_user = run(add_user_command, capture_output=True, shell=True, encoding="utf8")

        # If there is an error during the creation of the user, the process is cancelled
        if add_user.stderr: 
            return {"msg": add_user.stderr, "status": 409}
        set_policy_command = "./mc admin policy set iehr name_policy user=" + username
        set_policy = run(set_policy_command, capture_output=True, shell=True, encoding="utf8")

        if set_policy.stderr:
            return {"msg": set_policy.stderr, "status":409}
        
        new_user = {"username": username}
        # new_user = {"username": username, "password": password}
        users.insert_one(new_user)
        bucket_creation_res = make_bucket(username)
        return {"msg": "The user is created", "status": 200}
    
    else: 
        return {"msg": "User with the current username already exists", "status": 409}

def set_consent_to_store_true(username): 
    if users.find({"username": username}).count():
        users.update_one({"username":username}, {"$set": {"consent_store": "True"}})
        return {"msg": "User has agreed to store data on the S-EHR Cloud", "status": 200}
    else: 
        return {"msg":"Something went wrong", "status": 400}

def set_consent_to_share_true(username): 
    if users.find({"username": username}).count():
        users.update_one({"username":username}, {"$set": {"consent_share": "True"}})
        return {"msg": "User has agreed to share data with HCPs", "status": 200}
    else: 
        return {"msg":"Something went wrong", "status": 400}

def check_consent_to_store_exists(username): 
    if users.find({"username": username, "consent_store": {"$exists": True}}).count():
        return {"msg": "User has agreed to store data on the S-EHR Cloud", "status": 200, "consentStore": True}
    else: 
        return {"msg":"User must first agree to the consent to store data on the S-EHR Cloud", "status": 400, "consentStore": False}

def check_consent_to_share_exists(username): 
    if users.find({"username": username, "consent_share": {"$exists": True}}).count():
        return {"msg": "User has agreed to share data with HCPs", "status": 200, "consentShare": True}
    else: 
        return {"msg":"User must first agree to share data with HCPs", "status": 400, "consentShare": False}

def check_consent_to_store_exists(username): 
    if users.find({"username": username, "consent_store": {"$exists": True}}).count():
        return {"msg": "User has agreed to store data with HCPs", "status": 200, "consentStore": True}
    else: 
        return {"msg":"User must first agree to store data on the S-EHR Cloud", "status": 400, "consentStore": False}

def withdraw_consent_share(username):
    # consent_share_exists = users.find({"username": username, "consent_share": {"$exists": True}}).count()
    users.update_one({"username": username}, {"$unset":{"consent_share": ""}})
    return {"msg":"User no longer agrees to share data with HCPs", "status": 400, "consentShare": False}

def download_ho_audit_info(username):
    ho_granted_access = users.find({"username": username}, {"healthcare_organizations_granted_access": 1, "_id":0})
    return ho_granted_access[0]

def remove_user(username):
    '''
        This function removes the user's account and deletes their health data from the S-EHR Cloud. 
        Prior to the deletion of the account the data is dropped, hence the delete_bucket() function is called. 
        Then the user is deleted from the MinIO storage cloud and the MongoDB.
    '''
    bucket_deleted = delete_bucket(username=username)
    if bucket_deleted['response'] is 'OK':
        if users.find({"username":username}).count() != 0:
            remove_user_command = "./mc admin user remove iehr " + username
            remove_user = run(remove_user_command, capture_output=True, shell=True, encoding="utf8")

            # If there is an error during the creation of the user, the process is cancelled
            if remove_user.stderr: 
                return {"msg": remove_user.stderr, "status": 409}

            bucket_deleted = delete_bucket(username=username)
            
            user_for_deletion = {"username": username}
            mongo_user_deleted = users.delete_one(user_for_deletion)
            return {'msg': 'user\'s account is deleted', 'status': 400, 'mongodb_result': str(mongo_user_deleted)}    
    else: 
        return {'msg': 'user not found', 'status': 409}

def make_bucket(username):
    try: 
        res = admin_user.make_bucket(bucket_name=username)
        return res
    except ResponseError as err: 
        return err
    except BucketAlreadyExists as err: 
        return err

def delete_bucket(username):
    # This function is used to remove the citizen's bucket along with its content. 
    # The '--force' flag is used in order to force remove the bucket even if it is not empty (i.e. EHR content is uploaded)
    delete_bucket_command = "./mc rb --force iehr/" + username
    remove_user = run(delete_bucket_command, capture_output=True, shell=True, encoding="utf8")
    return {'response': 'OK'}

def create_hcp(citizen_username, hospital):
    hcp_username = citizen_username+"emergency"+hospital
    print(hcp_username)
    if hcps.find({"hcp_username":hcp_username}).count() == 0:
        
        hcp_password = generate_password()
        policy = open('policy_hcp.json', 'r')
        policy_string = ""
        for line in policy:
            policy_string += line
        policy_json = json.loads(policy_string)
        current_policy_0 = policy_json['Statement'][0]['Resource']
        current_policy_0.append("arn:aws:s3:::"+citizen_username)
        current_policy_0.append("arn:aws:s3:::"+hcp_username)
        current_policy_0.append("arn:aws:s3:::"+citizen_username+"/*")
        current_policy_0.append("arn:aws:s3:::"+hcp_username+"/*")


        current_policy_1 = policy_json['Statement'][1]['Resource']
        current_policy_1.append("arn:aws:s3:::"+citizen_username)
        current_policy_1.append("arn:aws:s3:::"+hcp_username)
        current_policy_1.append("arn:aws:s3:::"+citizen_username+"/*")
        current_policy_1.append("arn:aws:s3:::"+hcp_username+"/*")

        with open('policy_hcp_new.json', 'w') as new_policy_file:
            json.dump(policy_json, new_policy_file)  

        # Create new dedicated policy
        add_policy_command = "./mc admin policy add iehr hcp_policy policy_hcp_new.json"
        add_policy = run(add_policy_command, capture_output=True, shell=True, encoding="utf8")

        if add_policy.stderr:
            return {"msg": add_policy.stderr, "status": 409}
        
        # Create new emergency user
        add_hcp_command = "./mc admin user add iehr "+ hcp_username +" "+ hcp_password
        print(add_hcp_command)
        add_hcp = run(add_hcp_command, capture_output=True, shell=True, encoding="utf8")


        if add_hcp.stderr:
            return {"msg": add_hcp.stderr, "status": 409}

        set_policy_command = "./mc admin policy set iehr hcp_policy user=" + hcp_username
        set_policy = run(set_policy_command, capture_output=True, shell=True, encoding="utf8")

        if set_policy.stderr:
            return {"msg": set_policy.stderr, "status":409}
    
        # Add the HCP to the MongoDB
        new_hcp = {"username": hcp_username}
        hcps.insert_one(new_hcp)
        
        # audit_hco_granted_access(citizen_username, hospital)
        
        try: 
            bucket_creation_res = make_bucket(hcp_username)
        except BucketAlreadyOwnedByYou as err:
            return {'msg': err.message, "status":400}
        except BucketAlreadyExists as err: 
            return {'msg': err.message, "status":400}

        return {"msg": "The HCP is created", "status": 200}
    
    else: 
        # audit_hco_granted_access(citizen_username, hospital)
        return {"msg": "The HCP already exists", "status": 409}

def audit_hco_granted_access(citizen_username, hospital):
    healthcare_organization = {"healthcare_organization": hospital, "access_granted_date": str(datetime.datetime.utcnow())}
    users.update_one({"username":citizen_username}, {"$push": {"healthcare_organizations_granted_access": healthcare_organization}})

# def audit_hco_downloaded_hr(citizen_username, hospital, hr_name):
#     healthcare_organization = {"healthcare_organization": hospital, "access_granted_date": str(datetime.datetime.utcnow())}
#     users.update_one({"username":citizen_username})