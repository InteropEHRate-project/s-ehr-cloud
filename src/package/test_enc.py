from subprocess import run, check_output

from minio.api import Minio
from minio.error import BucketAlreadyExists, ResponseError
from instance.enc_config import ENC
from fernet import Fernet
from simplecrypt import encrypt, decrypt
import json

from instance.minio_config import MINIO_CONFIG

admin_user = Minio(MINIO_CONFIG['MINIO_ENDPOINT'], 
                    access_key=MINIO_CONFIG['MINIO_ACCESS_KEY'],
                    secret_key=MINIO_CONFIG['MINIO_SECRET_KEY'],
                    secure=MINIO_CONFIG['MINIO_SECURE'])

def make_bucket(username):
    try: 
        res = admin_user.make_bucket(bucket_name=username)
        return res
    except ResponseError as err: 
        return err
    except BucketAlreadyExists as err: 
        return err

def create_hcp(citizen_username, hospital):
    policy = open('policy_hcp.json', 'r')
    policy_string = ""
    for line in policy:
        policy_string += line
    policy_json = json.loads(policy_string)
    current_policy_0 = policy_json['Statement'][0]['Resource']
    current_policy_0.append("arn:aws:s3:::"+citizen_username)
    current_policy_0.append("arn:aws:s3:::"+citizen_username+"emergency")
    print(current_policy_0)
    current_policy_1 = policy_json['Statement'][1]['Resource']
    current_policy_1.append("arn:aws:s3:::"+citizen_username)
    current_policy_1.append("arn:aws:s3:::"+citizen_username+"emergency")
    print(current_policy_1)

    with open('policy_hcp_new.json', 'w') as new_policy_file:
        json.dump(policy_json, new_policy_file)  

    # Create new dedicated policy
    add_policy_command = "./mc admin policy add iehr hcp_policy policy_hcp_new.json"
    add_policy = run(add_policy_command, capture_output=True, shell=True, encoding="utf8")

    if add_policy.stderr:
        return "something went wrong!"
        # return {"msg": add_policy.stderr, "status": 409}

    # Create new emergency user
    add_hcp_command = "./mc admin user add iehr "+citizen_username+"emergency !jhasdj1238u1!d"
    add_hcp = run(add_hcp_command, capture_output=True, shell=True, encoding="utf8")

    # If there is an error during the creation of the user, the process is cancelled
    if add_hcp.stderr:
        return "something went wrong!!" 
        # return {"msg": add_hcp.stderr, "status": 409}

    set_policy_command = "./mc admin policy set iehr hcp_policy user=" + citizen_username+"emergency"
    set_policy = run(set_policy_command, capture_output=True, shell=True, encoding="utf8")

    if set_policy.stderr:
        return "something went wrong!!!"
        # return {"msg": set_policy.stderr, "status":409}

    bucket_creation_res = make_bucket(citizen_username+"emergency")
    print(bucket_creation_res)
    return "all good!"
    # return {"msg":"hcp account is created"}    
    #     # new_user = {"username": citizen_username}
    #     # # new_user = {"username": username, "password": password}
    #     # users.insert_one(new_user)
    #     # bucket_creation_res = make_bucket(citizen_username)
    #     # return {"msg": "The user is created", "status": 200}
    # else:
    #     return {"msg": "User with the current username already exists", "status": 409}

res = create_hcp("thisisatest1233", 123)
print(res)
