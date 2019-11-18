FROM pcic/geospatial-python
MAINTAINER Mike McCann <mccann@mbari.org>

# Modeled after http://michal.karzynski.pl/blog/2015/04/19/packaging-django-applications-as-docker-container-images/

# Additional requirements for stoqs not in pcic/geospatial-python
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && \
    apt-get -qq -y install \
    freetds-dev \
    git \
    gmt \
    libncurses-dev \
    postgresql-10 \
    time \
    wget \
    imagemagick \
    firefox \
    xvfb

# For running functional tests
RUN wget -q "https://github.com/mozilla/geckodriver/releases/download/v0.24.0/geckodriver-v0.24.0-linux32.tar.gz" -O /tmp/geckodriver.tgz \
    && tar zxf /tmp/geckodriver.tgz -C /usr/bin/ \
    && rm /tmp/geckodriver.tgz

# Set the locale
RUN locale-gen en_US.UTF-8
ENV LANG='en_US.UTF-8' LANGUAGE='en_US:en' LC_ALL='en_US.UTF-8'

# To fix multiprocessing-permission-denied for docker-compose execution
RUN echo 'none /dev/shm tmpfs rw,nosuid,nodev,noexec 0 0' > /etc/fstab

# Make sure python and python-config refer to corresponding Python 3 versions
RUN cd /usr/bin/ &&\
    ln -fs python3 python &&\
    ln -fs python3-config python-config

WORKDIR /srv

# Symlink to requirements from docker directory used to minimize context
COPY requirements /requirements
RUN pip3 install -U git+https://github.com/matplotlib/basemap.git
RUN /bin/bash -c 'pip install -r /requirements/production.txt'

# Connection to uwsgi/nginx
COPY docker-stoqs-uwsgi.ini /etc/uwsgi/django-uwsgi.ini

CMD ["docker/stoqs-start.sh"]

