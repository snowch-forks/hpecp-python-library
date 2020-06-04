#!/usr/bin/env bash

# (C) Copyright [2020] Hewlett Packard Enterprise Development LP
# 
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the "Software"),
# to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense,
# and/or sell copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.  IN NO EVENT SHALL
# THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR
# OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
# ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
# OTHER DEALINGS IN THE SOFTWARE.

set -u

if [[ ! -d ~/.aws  ]]; then
   if [[ ! -d /workspace/.aws ]]; then
       echo "Please run utils/hpecp_configure.sh"
       exit 1
   else
       ln -sf /workspace/.aws ~/.aws
   fi
fi

if [[ ! -f ~/.hpecp_service  ]]; then
   if [[ ! -f /workspace/.hpecp_service ]]; then
       echo "Please run utils/hpecp_configure.sh"
       exit 1
   else
       ln -sf /workspace/.hpecp_service ~/.hpecp_service
   fi
fi
source ~/.hpecp_service

aws ec2 create-network-acl-entry \
    --network-acl-id $NACL_ID \
    --cidr-block "$(curl -s http://ifconfig.me/ip)/32" \
    --ingress \
    --protocol -1 \
    --rule-action allow \
    --rule-number 110

if [[ $? != 0 ]]; then
    aws ec2 replace-network-acl-entry \
        --network-acl-id $NACL_ID \
        --cidr-block "$(curl -s http://ifconfig.me/ip)/32" \
        --ingress \
        --protocol -1 \
        --rule-action allow \
        --rule-number 110
fi

aws ec2 authorize-security-group-ingress \
    --group-id $SG_ID \
    --protocol all \
    --port -1 \
    --cidr "$(curl -s http://ifconfig.me/ip)/32"
