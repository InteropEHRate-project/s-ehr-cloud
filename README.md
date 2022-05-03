# Smart-EHR Cloud (S-EHR Cloud)

The S-EHR Cloud is a service offered by the InteropEHRate project, as a reference implementation of a service for cloud storage of S-EHR content. 

### Installation Guide
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
* Endpoint: 
* Description: 
* Response: 

### Retrieve a list of the buckets connected to the citizen’s account
* Endpoint: 
* Description: 
* Response: 

### Retrieve a list of objects stored in a bucket
* Endpoint: 
* Description: 
* Response: 

### Download metadata information for an encrypted health record
* Endpoint: 
* Description: 
* Response: 

### Download an encrypted health record from the S-EHR Cloud 
* Endpoint: 
* Description: 
* Response: 

### Upload an encrypted health record to the S-EHR Cloud
* Endpoint: 
* Description: 
* Response: 

### Revoke the consent that allows the S-EHR Cloud provider to share the citizen’s health data with authorized Healthcare Institutions
* Endpoint: 
* Description: 
* Response: 

### Remove the account and delete the health data stored in the S-EHR Cloud
* Endpoint: 
* Description: 
* Response: 


