#!/bin/bash

# If you want to launch the graphics, uncomment this
if [ ${GRAPHICS} ]; then
    /usr/bin/supervisord -c /etc/supervisor/supervisord.conf &
fi

# TODO: launch your element and anything else needed here.
echo "Hello, world!"
