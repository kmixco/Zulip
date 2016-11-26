FROM ubuntu:trusty

RUN apt-get update && apt-get install -y \
  python-pbs \
  wget

RUN locale-gen en_US.UTF-8

RUN useradd -d /home/zulip -m zulip && echo 'zulip ALL=(ALL) NOPASSWD:ALL' >> /etc/sudoers

USER zulip

RUN ln -nsf /srv/zulip ~/zulip

RUN echo 'export LC_ALL="en_US.UTF-8" LANG="en_US.UTF-8" LANGUAGE="en_US.UTF-8"' >> ~zulip/.bashrc

WORKDIR /srv/zulip

CMD ["/usr/bin/python /srv/zulip/tools/provision.py","--docker"]
CMD ["source /srv/zulip-venv/bin/activate"]
CMD ["./srv/zulip/tools/start-dockers"]

EXPOSE 9991