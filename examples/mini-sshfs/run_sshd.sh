#!/bin/bash

PORT=${MINI_SSHD_PORT:-2022}
SSHD=${SSHD:-/usr/sbin/sshd}
HERE=$(dirname $(realpath $0))

mkdir -p $HERE/.keys
pushd $HERE/.keys
[ -f ssh_host_rsa_key     ] || ssh-keygen -f ssh_host_rsa_key     -t rsa     -N ""
[ -f ssh_host_ecdsa_key   ] || ssh-keygen -f ssh_host_ecdsa_key   -t ecdsa   -N ""
[ -f ssh_host_ed25519_key ] || ssh-keygen -f ssh_host_ed25519_key -t ed25519 -N ""
[ -f ssh_user_ed25519_key ] || ssh-keygen -f ssh_user_ed25519_key -t ed25519 -N ""
popd

pushd $HERE
cat .keys/ssh_host_*_key.pub | awk -F' ' '{ print "localhost " $1 " " $2}' > known_hosts
cat .keys/ssh_user_*_key.pub > authorized_keys

export HERE PORT
envsubst '$HERE,$USER,$PORT' < sshd_config.template > sshd_config
$SSHD -f ./sshd_config -D
popd
