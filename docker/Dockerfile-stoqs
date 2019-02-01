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
    imagemagick

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

# Build and install geos - needed for basemap (several warnings/errors on compiling that can be ignored)
RUN echo '/usr/local/lib' >> /etc/ld.so.conf
RUN wget -q -N http://download.osgeo.org/geos/geos-3.6.0.tar.bz2
RUN tar -xjf geos-3.6.0.tar.bz2
RUN cd geos-3.6.0 && ./configure && make -j 2 && make install && ldconfig && cd ..

# Symlink to requirements from docker directory used to minimize context
COPY requirements /requirements
RUN pip3 install git+https://github.com/pymssql/pymssql
RUN /bin/bash -c 'pip install -r /requirements/production.txt'

# Basemap install - needed for monitorLrauv.py in production (some warnings/errors on compiling that can be ignored)
RUN wget -q http://sourceforge.net/projects/matplotlib/files/matplotlib-toolkits/basemap-1.0.7/basemap-1.0.7.tar.gz
RUN tar -xzf basemap-1.0.7.tar.gz
RUN cd basemap-1.0.7 && GEOS_DIR=/usr/local python setup.py install && cd ..

# Connection to uwsgi/nginx
COPY docker-stoqs-uwsgi.ini /etc/uwsgi/django-uwsgi.ini

CMD ["docker/stoqs-start.sh"]

