ARG ATOM_IMAGE=elementaryrobotics/atom:v1.7.0-stock-amd64
FROM ${ATOM_IMAGE}

ARG DEBIAN_FRONTEND=noninteractive

# Update Dependencies
RUN apt-get -y update && apt-get install -y build-essential python3-tk python3-dev libpng-dev

# Want to copy over the contents of this repo to the code
#	section so that we have the source
ADD . /code

# Here, we'll build and install the code s.t. our launch script,
#	now located at /code/launch.sh, will launch our element/app
WORKDIR /code
RUN pip3 install wheel
# Need to let matplotlib know it can download freetype
ENV MPLLOCALFREETYPE=1
RUN pip3 install -r requirements.txt

#
# TODO: build code
#

# Finally, specify the command we should run when the app is launched
RUN chmod +x launch.sh
CMD ["/bin/bash", "launch.sh"]
