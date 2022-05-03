from datetime import datetime
from time import time
from pymongo import MongoClient
from minio import Minio, ResponseError
from minio.error import InvalidBucketError, InvalidBucketName, ResponseError, InvalidAccessKeyId, InvalidArgument, InvalidArgumentError, SignatureDoesNotMatch, AccessDenied, NoSuchKey
from subprocess import check_output, run
from instance.minio_config import MINIO_CONFIG
from instance.mongodb_config import MONGODB_CONFIG
import package.admin as cloud_admin
import package.audit as audit
import package.hco_authorization as hco_authorization
import os 
import datetime
import json

mongo_client = MongoClient(MONGODB_CONFIG["MONGODB_ENDPOINT"])
db = mongo_client['SEHR_Cloud']
users = db['Users']

class HCP: 

    def create_hcp_account(self, citizen_username, hospital, hcp_name, hco_certificate):
        """ 
        An account in S-EHR Cloud is created for emergency purposes. 
        After the account creation, a bucket is created for the HCP to store EHRs related to the emergency and a policy allowing 
        the HCP to only view this and the citizen's bucket is applied.  
        """
        
        # Checking certificate validity in the CA
        ca_status, is_certificate_valid = hco_authorization.is_hco_authorized(hco_certificate)
        print(is_certificate_valid)
        if (is_certificate_valid.startswith("O=EJBCA Container Quickstart, CN=ManagementCA")):
            self.set_citizen_username(citizen_username)
            self.set_hospital(hospital)
            res = cloud_admin.create_hcp(citizen_username, hospital)
            self.set_hcp_username()
            self.set_password()
            audit.audit_hco_granted_access(citizen_username, hcp_name, hospital)
        else: 
            res = {"msg": "The HCO could not be authorized", "status": 403}
        
        return res

    def set_hcp(self):
        try:
            self.hcp = Minio(MINIO_CONFIG['MINIO_ENDPOINT'], 
                                    access_key=self.hcp_username, 
                                    secret_key=self.password, 
                                    secure=MINIO_CONFIG['MINIO_SECURE'])
            # self.hcp.list_buckets()
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

    def set_hospital(self, hospital):
        self.hospital =  hospital
    
    def get_hospital(self):
        return self.hospital

    def set_hcp_username(self):
        self.hcp_username =  self.citizen_username+"emergency"+self.hospital
    
    def get_hcp_username(self):
        return self.hcp_username

    def set_citizen_username(self, citizen_username):
        self.citizen_username = citizen_username

    def set_password(self):
        self.password = "!jhasdj1238u1!d"

    def get_citizen_username(self):
        return self.citizen_username

    def get_password(self):
        return self.password

# Method for HCP's account creation which sends back to the HCP
    def authenticate_hcp(self, citizen, hospital_name): 
        res = cloud_admin.create_hcp(citizen_username=citizen, hospital=hospital_name)
        return res

    def download_hr_file(self, bucket, object, hcp_name):
        try: 
            encrypted_hr_file = self.hcp.get_object(bucket_name=bucket, 
                                object_name=object)
            audit.audit_hco_download_file(bucket, hcp_name, self.get_hospital(), object)
            return encrypted_hr_file.read()
        except ResponseError as err: 
            return {'err': err.message, 'status': 'F'}
        except NoSuchKey as err: 
            return {'err': err.message, 'status': 'F'}
        except AccessDenied as err: 
            return {'err': err.message, 'status': 'F'}
        except InvalidBucketError as err: 
            return {'err': err.message, 'status': 'F'}
        except InvalidBucketName as err: 
            return {'err': err.message, 'status': 'F'}
    
    def upload_hr_file_string(self, encrypted_hr_file_in_bytes, encrypted_hr_file_as_stream, encrypted_hr_file_name, hcp_name, metadata=None):
        if metadata: 
            res = self.hcp.put_object(bucket_name=self.get_hcp_username(), 
                            object_name=encrypted_hr_file_name, 
                            data=encrypted_hr_file_as_stream, 
                            length=len(encrypted_hr_file_in_bytes), 
                            metadata=metadata)
            res = {'msg': res}
            audit.audit_hco_upload_file(self.get_citizen_username(), hcp_name, self.get_hospital(), encrypted_hr_file_name)
            return res
        else: 
            res = self.user.put_object(bucket_name=self.get_username(), 
                            object_name=encrypted_hr_file_name, 
                            data=encrypted_hr_file_as_stream, 
                            length=len(encrypted_hr_file_in_bytes)
                            )
            
            audit.audit_hco_upload_file(self.get_citizen_username(), hcp_name, self.get_hospital(), encrypted_hr_file_name)
            return {'msg': res}

    def list_objects(self, bucket):
        try:
            objects = self.hcp.list_objects(bucket_name=bucket)
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
            return {"err": "HCP is not granted access"}
        except AccessDenied: 
            return {"err": "Access denied"}
        except InvalidBucketError as err: 
            return {'err': err.message, 'status': 'F'}
        except InvalidBucketName as err: 
            return {'err': err.message, 'status': 'F'}

    def list_buckets(self):
        try:
            return self.hcp.list_buckets()
        except AttributeError as err: 
            return {"err": "HCP is not granted access", 'status': 'F'}
        except AccessDenied as err: 
            return {"err": err.message, 'status': 'F'}

    def stat_object(self, bucket_name, encrypted_object_name): 
        print(bucket_name)
        try: 
            res = self.hcp.stat_object(bucket_name=bucket_name, 
                                    object_name=encrypted_object_name)
            
            return {'metadata': res, 'status': 'OK'}
        except NoSuchKey as err: 
            return {'err': err.message, 'status': 'F'}
        except AccessDenied as err: 
            return {'err': err.message, 'status': 'F'}
        except InvalidBucketError as err: 
            return {'err': err.message, 'status': 'F'}
        except InvalidBucketName as err: 
            return {'err': err.message, 'status': 'F'}