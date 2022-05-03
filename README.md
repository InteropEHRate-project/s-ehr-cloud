# Smart-EHR Cloud (S-EHR Cloud)

The S-EHR Cloud is a service offered by the InteropEHRate project, as a reference implementation of a service for cloud storage of S-EHR content. 

## Installation Guide
In order to exploit the functionality of the S-EHR Cloud service, the user must have Docker and Docker Compose installed on the desired machine. Then, the GitHub repository provides all the files that are needed to run the service. The user must clone the repository found in the project’s GitHub server and afterwards has to navigate to the root of the project. At that moment, by running the following command: `docker-compose up -d` the three necessary containers will be instantiated. 

The first container regards the Gateway component that is responsible for managing incoming requests from citizens and healthcare professionals. This component is a Docker container built based on the Dockerfile provided within the repository. The second component regards a MinIO Object Storage used for the storage of encrypted health records. Finally, the third component regards a MongoDB database used for keeping auditing information. The service can be accessed by performing requests to `http://[URL]:5000`, followed by the desired endpoint.

## User Guide

The following endpoints can be used by the citizen in order to interact with the S-EHR Cloud and perform the following actions: 
### Registration to the S-EHR Cloud
* Endpoint: `[POST] http://[URL]:5000/citizen/register`
* Description: This operation allows a citizen to send a request to create an account to a S-EHR Cloud provider. As soon as the account is created, a bucket linked to this account is created as well. This bucket is used to store the encrypted health data of the citizen. 
* Response: 
```
{
    “msg” : String: Message related to the citizen’s account creation, 
}
```

### Login to the S-EHR Cloud
* Endpoint: `[POST] http://[URL]:5000/citizen/login`
* Description: This operation allows a citizen to send a request to login to the S-EHR Cloud. 
* Response: 
```
{
    “token” : JSON Web Token: Citizen’s Authorization token, 
    “emergencyToken” : JSON Web Token: Healthcare Institution emergency token
}
```

### Download consent to allow the S-EHR Cloud provider to store the citizen’s health data in an encrypted format
* Endpoint: `GET] http://[URL]:5000/citizen/consent/cloud`
* Description: This operation allows a citizen to send a request to download the consent that allows the S-EHR Cloud to store the citizen’s health data. 
* Response: 
```
The consent that after signing it and re-uploading it on the S-EHR Cloud allows the service to store the citizen’s encrypted health data for backup purposes.
```

### Sign the consent to allow the S-EHR Cloud provider to store the citizen’s health data in an encrypted format
* Endpoint: `[POST] http://[URL]:5000/citizen/consent/cloud`
* Description: This operation allows a citizen to upload the signed consent that allows the S-EHR Cloud to store the citizen’s health data. 
* Response: 
```
{
   “msg” : String: Consent upload acknowledgement
}
```

### Download consent to allow the S-EHR Cloud provider to share the citizen’s health data with authorized Healthcare Institutions
* Endpoint: `[GET] http://[URL]:5000/citizen/consent/hco`
* Description: This operation allows a citizen to send a request to download the consent that allows the S-EHR Cloud to share the citizen’s health data with HCPs from authorized Healthcare Organizations. 
* Response: 
```
The consent that after signing it and re-uploading it on the S-EHR Cloud allows the service to share the citizen’s health data with HCPs from authorized Healthcare Organizations.
```

### Sign the consent to allow the S-EHR Cloud provider to share the citizen’s health data with authorized Healthcare Institutions
* Endpoint: `[POST] http://[URL]:5000/citizen/consent/hco`
* Description: This operation allows a citizen to upload the signed consent that allows the S-EHR Cloud to share the citizen’s health data with authorised Healthcare Institutions. 
* Response: 
```
{
   “msg” : String: Consent upload acknowledgement, 
   “emergencyToken” : JSON Web Token: Healthcare Institution emergency token
}
```

### Retrieve a list of the buckets connected to the citizen’s account
* Endpoint: `[GET] http://[URL]:5000/citizen/buckets`
* Description: This operation allows a citizen to send a request to retrieve the list of the buckets that this citizen can gain access to. 
* Response: 
```
{
    “buckets” : [
	    String: Bucket Name 1, 
	    String: Bucket Name 2, 
	    ...
	]
}
```

### Retrieve a list of objects stored in a bucket
* Endpoint: `[GET] http://[URL]:5000/citizen/buckets/{$bucketName}`
* Description: This operation allows a citizen to send a request to retrieve the list of the objects (i.e. the encrypted health data) stored in a specific bucket.
* Response: 
```
{
	“bucket”: String: Bucket name, 
	“objects” : [
		String: Bucket Name 1, 
		String: Bucket Name 2, 
		...
	]
}
```

### Download metadata information for an encrypted health record
* Endpoint: `[GET] http://[URL]:5000/citizen/{$bucketName}/{$objectName}/metadata`
* Description: This operation allows a citizen to send a request to download the metadata of an encrypted health record from the S-EHR Cloud. 
* Response: 
```
{
	“object” : String: Object Name, 
	“metadata”: {
		“objectName”: String: Object Name, 
		“bucketName”: String: Bucket Name,
		“size”: Float: Size of the object in KB,
		“type”: String: Object type, 
		“dateAdded”: Date: Date stored in S-EHR Cloud
	}
}
```

### Download an encrypted health record from the S-EHR Cloud 
* Endpoint: `[GET] http://[URL]:5000/citizen/{$bucketName}/{$ResourceCategory}`
* Description: This operation allows a citizen to send a request to download an encrypted health data resource from the citizen’s bucket and decrypt it locally on the S-EHR Mobile app.
* Response: 
```
The requested health record in an encrypted binary file format.
```

### Upload an encrypted health record to the S-EHR Cloud
* Endpoint: `[POST] http://[URL]:5000/citizen/upload?objectName={$ResourceCategory} `
* Description: This operation allows a citizen to send a request to upload an encrypted FHIR Bundle containing health data of the authenticated citizen.
* Response: 
```
“msg” : String: Health record upload acknowledgement
```

### Revoke the consent that allows the S-EHR Cloud provider to share the citizen’s health data with authorized Healthcare Institutions
* Endpoint: `[DELETE] http://[URL]:5000/citizen/consent/hco`
* Description: This operation revokes the previously signed consent, thus the S-EHR Cloud is no longer allowed to share the citizen’s health data with HCPs from trusted Healthcare Organizations. 
* Response: 
```
{
    “msg” : String: Consent revocation acknowledgement
}
```

### Remove the account and delete the health data stored in the S-EHR Cloud
* Endpoint: `[DELETE] http://[URL]:5000/citizen/account`
* Description: This operation deletes the citizen’s account from the S-EHR Cloud and removes all the data that is stored in the S-EHR Cloud related to this citizen.
* Response: 
```
{
    “msg” : String: Account removal acknowledgement
}
```

### Retrieve audit information
* Endpoint: `[GET] http://[URL]:5000/citizen/auditing`
* Description: This operation allows a citizen to download audit information regarding the Healthcare Organizations that were granted access to the S-EHR Cloud, and any changes made to the citizen’s health records.
* Response: 
```
"auditing": {
    "hr_info": {
        "uploaded": [{
            "uploaded_hr": "$hrName",
            "hr_uploaded_on": "$timestamp"
        }, 
        ...
        ],
        "downloaded": [{
            "downloaded_hr": "$hrName",
            "hr_downloaded_on": "$timestamp"
        }, 
        ...
        ]
    },
    "hco": {
        "granted_access": [{
            "healthcare_organization_name": "$hcoName",
            "granted_access_on": "$timestamp", 
            "healthcare_professionals_granted_access": [
                "$hcp1Name", 
                "$hcp2Name", 
                ... 
            ]
        }, 
        ...
        ],
        "downloaded": [{
            "healthcare_organization_name": "$hcoName",
            "healthcare_professional_name": "$hcpName",
            "downloaded_hr_on": "$timestamp",
            "downloaded_hr": "$hrName"
        }, 
        ...
        ],
        "uploaded": [{
            "healthcare_organization_name": "$hcoName",
            "healthcare_professional_name": "$hcpName",
            "downloaded_hr_on": "$timestamp",
            "downloaded_hr": "$hrName"
        }, 
        ...
        ]
    }
}
```
___
The following endpoints can be utilized by HCPs from trusted Healthcare Institutions in order to perform the following actions: 

### Request access to a citizen’s health data stored in the S-EHR Cloud
* Endpoint: `[POST] http://[URL]:5000/hcp/requestaccess`
* Description: his operation allows an HCP from a Healthcare Institution to send a request to access the citizen’s health data stored in the S-EHR Cloud during an emergency.
* Response:
```
{
    “msg” : String: Access Request acknowledgement,
    “hcoEmergencyToken” : Healthcare Institution Authorization JSON Web Token
}
```

### Retrieve a list of the buckets that can be accessed by the Healthcare Institution’s temporary account
* Endpoint: `[GET] http://[URL]:5000/hcp/buckets`
* Description: This operation allows an HCP, using their Healthcare Institution’s temporary account, to retrieve the list of the buckets that their account can gain access to.
* Response: 
```
{
	“buckets” : [
		String: Bucket Name 1, 
		String: Bucket Name 2, 
		...
	]
}
```
### Retrieve a list of objects stored in a bucket
* Endpoint: `[GET] http://[URL]:5000/hcp/buckets/{$bucketName}`
* Description:  This operation allows an HCP, using their Healthcare Institution’s temporary account, to retrieve the list of the objects (i.e. the encrypted health data) stored in a specific bucket.
* Response: 
```
{
	“bucket” : String: Bucket Name, 
	“objects” : [
		"$encryptedHrName1", 
		"$encryptedHrName2", 
		...
	]
}
```

### Download metadata information for an encrypted health record
* Endpoint: `[GET] http://[URL]:5000/hcp/{$bucketName}/{$ResourceCategory}/metadata`
* Description: This operation allows an HCP, using their Healthcare Institution’s temporary account, to retrieve the metadata of an encrypted health record from the S-EHR Cloud.
* Response: 
```
{
	“object” : String: Object Name, 
	“metadata”: {
		“objectName”: String: Object Name, 
		“bucketName”: String: Bucket Name,
		“size”: Float: Size of the object in KB,
		“type”: String: Object type, 
		“dateAdded”: Date: Date stored in S-EHR Cloud
	}
}
```

Download an encrypted health record from the S-EHR Cloud 
* Endpoint: `[GET] http://[URL]:5000/hcp/{$bucketName}/{$ResourceCategory}`
* Description: This operation allows an HCP, using their Healthcare Institution’s temporary account, to download an encrypted health data record from the S-EHR Cloud and decrypt it locally on the HCP App. 
* Response: 
```
The requested health record in an encrypted binary file format.
```

Upload an encrypted health record to the S-EHR Cloud
* Endpoint: `[POST] http://[URL]:5000/hcp/upload?objectName={$ResourceCategory}`
* Description: This operation allows an HCP, using their Healthcare Institution’s temporary account, to upload an encrypted health data’s information to the S-EHR Cloud. 
* Response: 
```
{
	“msg” : String: Health record upload acknowledgement
}
```

