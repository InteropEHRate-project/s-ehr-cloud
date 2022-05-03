FROM ubuntu:16.04 
RUN apt-get update
RUN apt-get install -y python3 python3-pip python3-virtualenv

RUN mkdir sehr_cloud

# Installing requirements
COPY requirements.txt sehr_cloud/requirements.txt
COPY setup.py sehr_cloud/setup.py
RUN cd sehr_cloud; pip install -e .

COPY src/ sehr_cloud/src
COPY mc sehr_cloud/mc
COPY policy.json sehr_cloud/policy.json
COPY policy_hcp.json sehr_cloud/policy_hcp.json
COPY consent_share.json sehr_cloud/consent_share.json
COPY consent_store.json sehr_cloud/consent_store.json

# ENV VIRTUAL_ENV=/opt/venv
# RUN python3 -m virtualenv --python=/usr/bin/python3 $VIRTUAL_ENV
# ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# COPY requirements.txt requirements.txt
# RUN pip install -r requirements.txt
# RUN mkdir /sehr_cloud
# COPY setup.py setup.py
# RUN pip install -e .

# COPY /src /sehr_cloud/src
# RUN /sehr_cloud
WORKDIR /sehr_cloud/src/api  
EXPOSE 5000
ENTRYPOINT [ "python3","-u", "api.py" ]