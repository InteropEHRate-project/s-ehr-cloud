from instance.mongodb_config import MONGODB_CONFIG
from pymongo import MongoClient
import datetime

mongo_client = MongoClient(MONGODB_CONFIG["MONGODB_ENDPOINT"])
db = mongo_client['SEHR_Cloud']
users = db['Users']
hcps = db['HCP']

def get_audit_info(username):
    res = users.find_one({"username":username}, {"auditing":1, "_id":0})
    return res

def audit_user_upload_file(username, filename):
    users.update_one({"username":username},
                     {
                         "$push":{
                             "auditing.hr_info.uploaded":
                                 {
                                    "uploaded_hr":filename,
                                    "uploaded_on": str(datetime.datetime.utcnow())
                                 }
                         }
                     })
    
def audit_user_download_file(username, filename):
    users.update_one({"username":username},
                     {
                         "$push":{
                             "auditing.hr_info.downloaded":
                                 {
                                    "downloaded_hr":filename,
                                    "downloaded_on": str(datetime.datetime.utcnow())
                                 }
                         }
                     })

def audit_hco_granted_access(username, hco_name):
    hco_exists = check_if_hco_exists(username, hco_name)
    print(hco_exists)
    if hco_exists == None:
        users.update_one({"username":username},
                    {
                        "$push":{
                            "auditing.hco":
                                {
                                    "healthcare_organization_name":hco_name
                                }
                        }
                    })
    
    audit_add_granted_access_info(username, hco_name)
        
def audit_add_granted_access_info(username, hco_name):
    users.update_one({"$and":[
                        {
                            "username":username
                        },
                        { 
                            "auditing.hco.healthcare_organization_name":hco_name
                        }
                    ]
                },
                {
                    "$push":{
                        "auditing.hco.$.granted_access":str(datetime.datetime.utcnow())
                    }
                })

def check_if_hco_exists(username, hco_name):
    res = users.find_one({"$and":[
                        {
                            "username":username
                        },
                        { 
                            "auditing.hco.healthcare_organization_name":hco_name
                        }
                    ]
                })
    return res

def audit_hco_download_file(username, hco_name, file_name):
    users.update_one({"$and":[
                        {
                            "username":username
                        },
                        { 
                            "auditing.hco.healthcare_organization_name":hco_name
                        }
                    ]}, 
                    {
                        "$push":{
                            "auditing.hco.$.downloaded":{
                                "downloaded_hr":file_name, 
                                "downloaded_on":str(datetime.datetime.utcnow())
                            }
                        }
                    })

def audit_hco_upload_file(username, hco_name, file_name):
    users.update_one({"$and":[
                        {
                            "username":username
                        },
                        { 
                            "auditing.hco.healthcare_organization_name":hco_name
                        }
                    ]}, 
                    {
                        "$push":{
                            "auditing.hco.$.uploaded":{
                                "uploaded_hr":file_name, 
                                "uploaded_on":str(datetime.datetime.utcnow())
                            }
                        }
                    })
