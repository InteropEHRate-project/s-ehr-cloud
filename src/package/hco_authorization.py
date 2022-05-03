import requests

CA_URL = "http://interoperate-ejbca-service.euprojects.net/validatecertificate"

def is_hco_authorized(hco_certificate):
    response = requests.post(CA_URL, json= {"certificate": hco_certificate})
    print("CA STATUS CODE: \t" + str(response.status_code))
    print("CA RESPONSE BODY: \t" +str(response.text))
    return response.status_code, response.text
    