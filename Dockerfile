ARG ATOM_IMAGE=elementaryrobotics/atom:v1.7.0-stock-amd64
FROM ${ATOM_IMAGE}

ARG DEBIAN_FRONTEND=noninteractive

# Update Dependencies
RUN apt-get -y update

# Want to copy over the contents of this repo to the code
#	section so that we have the source
ADD . /code

# Here, we'll build and install the code s.t. our launch script,
#	now located at /code/launch.sh, will launch our element/app
WORKDIR /code
RUN apt-get install -y python3-tk
RUN pip3 install -r requirements.txt

#
# TODO: build code
#

# Finally, specify the command we should run when the app is launched
RUN chmod +x launch.sh
CMD ["/bin/bash", "launch.sh"]
