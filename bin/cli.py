#!/usr/bin/env python3

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

"""HPE Container Platform CLI."""

from __future__ import print_function

import base64
import configparser
import json
import os
import sys
from collections import OrderedDict

import fire

from jinja2 import Environment
import six
import traceback
import yaml
import wrapt

from hpecp import (
    APIException,
    APIItemConflictException,
    ContainerPlatformClient,
    ContainerPlatformClientException,
)
from hpecp.logger import Logger
from hpecp.k8s_cluster import (
    K8sCluster,
    K8sClusterHostConfig,
    K8sClusterStatus,
)
from hpecp.exceptions import (
    APIForbiddenException,
    APIItemNotFoundException,
    APIUnknownException,
)
from textwrap import dedent
import inspect
import collections
from hpecp.tenant import Tenant
from hpecp.user import User
from hpecp.role import Role
from hpecp.cli import base
from hpecp.cli.catalog import CatalogProxy
from hpecp.cli.gateway import GatewayProxy
from hpecp.cli.k8sworker import K8sWorkerProxy

if sys.version_info[0] >= 3:
    unicode = str

_log = Logger.get_logger()


@wrapt.decorator
def intercept_exception(wrapped, instance, args, kwargs):
    """Handle Exceptions."""  # noqa: D202

    def _unknown_exception_handler(ex):
        """Handle unknown exceptions."""
        if _log.level == 10:  # "DEBUG"
            print(
                "Unknown error.", file=sys.stderr,
            )
        else:
            print(
                "Unknown error. To debug run with env var LOG_LEVEL=DEBUG",
                file=sys.stderr,
            )
        tb = traceback.format_exc()
        _log.debug(tb)
        _log.debug(ex)
        sys.exit(1)

    try:
        return wrapped(*args, **kwargs)
    except SystemExit as se:
        sys.exit(se.code)
    except AssertionError as ae:
        print(ae, file=sys.stderr)
        sys.exit(1)
    except APIUnknownException as ue:
        _unknown_exception_handler(ue)
    except (
        APIException,
        APIItemNotFoundException,
        APIItemConflictException,
        APIForbiddenException,
        ContainerPlatformClientException,
    ) as e:
        print(e.message, file=sys.stderr)
        sys.exit(1)
    except Exception as ex:
        _unknown_exception_handler(ex)


class K8sClusterProxy(base.BaseProxy):
    """Proxy object to :py:attr:`<hpecp.client.k8s_cluster>`."""

    def __dir__(self):
        """Return the CLI method names."""
        return [
            "add_addons",
            "admin_kube_config",
            "create",
            "dashboard_url",
            "dashboard_token",
            "delete",
            "get",
            "get_available_addons",
            "get_installed_addons",
            "k8smanifest",
            "k8s_supported_versions",
            "list",
            "statuses",
            "wait_for_status",
        ]

    def __init__(self):
        """Create instance of proxy class with the client module name."""
        super(K8sClusterProxy, self).new_instance("k8s_cluster", K8sCluster)

    @intercept_exception
    def create(
        self,
        name,
        k8shosts_config,
        description=None,
        k8s_version=None,
        pod_network_range="10.192.0.0/12",
        service_network_range="10.96.0.0/12",
        pod_dns_domain="cluster.local",
        persistent_storage_local=False,
        persistent_storage_nimble_csi=False,
        addons=[],
    ):
        """Create a K8s Cluster.

        :param name: the cluster name
        :param k8shosts_config: k8s host ids and roles 'id1:master|worker,id2:
            master|worker,...'
        :param description: the cluster descripton
        :param k8s_version: e.g. 1.17.0
        :param pod_network_range: the pod network range,
            default='10.192.0.0/12'
        :param service_network_range: the service network range,
            default='10.96.0.0/12'
        :param pod_dns_domain: the pod dns domain, default='cluster.local'
        :param persistent_storage_local: True/False
        :param persistent_storage_nimble_csi: True/False
        :param addons: list of required addons. See:
            `hpecp k8scluster get-available-addons`
        """
        host_config = [
            K8sClusterHostConfig.create_from_list(h.split(":"))
            for h in k8shosts_config.split(",")
        ]

        print(
            base.get_client().k8s_cluster.create(
                name=name,
                description=description,
                k8s_version=k8s_version,
                pod_network_range=pod_network_range,
                service_network_range=service_network_range,
                pod_dns_domain=pod_dns_domain,
                persistent_storage_local=persistent_storage_local,
                persistent_storage_nimble_csi=persistent_storage_nimble_csi,
                k8shosts_config=host_config,
                addons=addons,
            )
        )

    def admin_kube_config(self, id):
        """Retrieve a K8s Cluster Admin Kube Config.

        :param id: the cluster ID
        """
        print(
            base.get_client()
            .k8s_cluster.get(id)
            .admin_kube_config.replace("\\n", "\n",)
        )

    def dashboard_url(
        self, id,
    ):
        """Retrieve a K8s Cluster Dashboard URL.

        :param id: the cluster ID
        """
        url = (
            base.get_client().k8s_cluster.get(id=id).dashboard_endpoint_access
        )
        print(url)

    def dashboard_token(
        self, id,
    ):
        """Retrieve a K8s Cluster Dashboard Token.

        :param id: the cluster ID
        """
        token = base.get_client().k8s_cluster.get(id=id).dashboard_token
        if six.PY2:
            print(base64.b64decode(token.encode()))
        else:
            print(base64.b64decode(token.encode()).decode("utf-8"))

    @intercept_exception
    def k8smanifest(self):
        """Retrieve the k8smanifest."""
        response = base.get_client().k8s_cluster.k8smanifest()
        print(
            yaml.dump(yaml.load(json.dumps(response), Loader=yaml.FullLoader,))
        )

    def get_installed_addons(self, id):
        """Retrieve the installed addons on the cluster.

        :param id: get installed addons for a specific cluster
        """
        print(base.get_client().k8s_cluster.get(id=id).addons)

    def get_available_addons(self, id=None, k8s_version=None):
        """Retrieve the available addons for a cluster.

        :param id: get available addons for a specific cluster (opt)
        :param k8s_version: get available addons for a cluster version (opt)
        """
        if id is not None and k8s_version is not None:
            print(
                "Either 'id' or 'k8s_version' parameter must be provided",
                file=sys.stderr,
            )
            sys.exit(1)

        if id is None and k8s_version is None:
            print(
                "Either 'id' or 'k8s_version' parameter must be provided",
                file=sys.stderr,
            )
            sys.exit(1)

        if id:
            print(base.get_client().k8s_cluster.get_available_addons(id=id))
        else:
            print(
                base.get_client().k8s_cluster.get_available_addons(
                    k8s_version=k8s_version
                )
            )

    def add_addons(self, id, addons, wait_for_ready_sec=0):
        """Retrieve the installed addons on the cluster.

        :param id: get installed addons for a specific cluster
        :param addons: list of addons to install
        :param wait_for_ready_sec: wait for ready status
        (0 = do not wait)
        """
        if id is None:
            print("'id' parameter must be provided.", file=sys.stderr)
            sys.exit(1)
        if addons is None or not isinstance(addons, list) or len(addons) < 1:
            print(
                "'addons' must be a list with at least one entry.",
                file=sys.stderr,
            )
            sys.exit(1)

        base.get_client().k8s_cluster.add_addons(id=id, addons=addons)

        if wait_for_ready_sec > 0:
            self.wait_for_status(
                id=id, status=["ready"], timeout_secs=wait_for_ready_sec
            )

    def statuses(self,):
        """Return a list of valid statuses."""
        print([s.name for s in K8sClusterStatus])

    def k8s_supported_versions(
        self,
        output="json",
        major_filter=None,
        minor_filter=None,
        patch_filter=None,
    ):
        """Print a list of supported k8s versions.

        :param output: how to print the output, 'json' or 'text'
        :param major_filter: only return versions matching major_filter
        :param minor_filter: only return versions matching minor_filter
        :param patch_filter: only return versions matching patch_filter

        Example::

        hpecp k8scluster k8s_supported_versions --major-filter 1
            --minor-filter 17
        """
        if output not in [
            "json",
            "text",
        ]:
            print(
                "'output' parameter ust be 'json' or 'text'", file=sys.stderr
            )
            sys.exit(1)

        if major_filter is not None and not isinstance(major_filter, int):
            print("'major_filter' if provided must be an int", file=sys.stderr)
            sys.exit(1)

        if minor_filter is not None and not isinstance(minor_filter, int):
            print("'minor_filter' if provided must be an int", file=sys.stderr)
            sys.exit(1)

        if patch_filter is not None and not isinstance(patch_filter, int):
            print("'patch_filter' if provided must be an int", file=sys.stderr)
            sys.exit(1)

        if major_filter:
            major_filter = int(major_filter)

        if minor_filter:
            minor_filter = int(minor_filter)

        if patch_filter:
            patch_filter = int(patch_filter)

        vers = []
        for v in base.get_client().k8s_cluster.k8s_supported_versions():
            (major, minor, patch) = v.split(".")
            major = int(major)
            minor = int(minor)
            patch = int(patch)
            if (
                (major_filter is not None and major != major_filter)
                or (minor_filter is not None and minor != minor_filter)
                or (patch_filter is not None and patch != patch_filter)
            ):
                continue
            else:
                vers.append(v)

        if output == "json":
            print(vers)
        else:
            print(" ".join(vers))


class TenantProxy(base.BaseProxy):
    """Proxy object to :py:attr:`<hpecp.client.tenant>`."""

    def __dir__(self):
        """Return the CLI method names."""
        return [
            "add_external_user_group",
            "assign_user_to_role",
            "create",
            "delete",
            "delete_external_user_group",
            "examples",
            "get",
            "get_external_user_groups",
            "k8skubeconfig",
            "list",
            # "status",  # TODO: implement me!
            "users",
            "wait_for_status",
        ]

    def __init__(self):
        """Create instance of proxy class with the client module name."""
        super(TenantProxy, self).new_instance("tenant", Tenant)

    @intercept_exception
    def create(
        self,
        name=None,
        description=None,
        tenant_type=None,
        k8s_cluster_id=None,
    ):
        """Create a tenant.

        Parameters
        ----------
        name : [type], optional
            [description], by default None
        description : [type], optional
            [description], by default None
        tenant_type : [type], optional
            [description], by default None
        k8s_cluster_id : [type], optional
            [description], by default None
        """
        tenant_id = base.get_client().tenant.create(
            name=name,
            description=description,
            tenant_type=tenant_type,
            k8s_cluster=k8s_cluster_id,
        )
        print(tenant_id)

    def examples(self):
        """Show usage_examples of the list method."""
        print(
            dedent(
                """\

                hpecp tenant list --query "[?tenant_type == 'k8s']" --output json-pp

                """  # noqa: E501
            )
        )

    @intercept_exception
    def k8skubeconfig(self):
        """Retrieve the tenant kubeconfig.

        This requires the ContainerPlatformClient to be created with
        a 'tenant' parameter.

        Returns
        -------
        str
            Tenant KubeConfig
        """
        conf = base.get_client().tenant.k8skubeconfig()
        print(conf)

    @intercept_exception
    def users(self, id, output="table", columns="ALL", query={}):
        """Retrieve users assigned to tenant.

        Parameters
        ----------
        id : str
            The tenant ID.
        """
        list_instance = base.get_client().tenant.users(id=id)
        self.print_list(
            list_instance=list_instance,
            output=output,
            columns=columns,
            query=query,
        )

    @intercept_exception
    def assign_user_to_role(self, tenant_id, user_id, role_id):
        """Assign user to role in tenant."""
        base.get_client().tenant.assign_user_to_role(
            tenant_id=tenant_id, user_id=user_id, role_id=role_id
        )

    @intercept_exception
    def get_external_user_groups(self, tenant_id):
        """Retrieve External User Groups."""
        print(
            base.get_client().tenant.get_external_user_groups(
                tenant_id=tenant_id
            )
        )

    @intercept_exception
    def add_external_user_group(self, tenant_id, group, role_id):
        """Add External User Group."""
        base.get_client().tenant.add_external_user_group(
            tenant_id=tenant_id, group=group, role_id=role_id
        )

    @intercept_exception
    def delete_external_user_group(self, tenant_id, group):
        """Delete External User Group."""
        base.get_client().tenant.delete_external_user_group(
            tenant_id=tenant_id, group=group
        )


class LockProxy(object):
    """Proxy object to :py:attr:`<hpecp.client.lock>`."""

    def __dir__(self):
        """Return the CLI method names."""
        return [
            "create",
            "delete",
            "delete_all",
            "list",
        ]

    def list(
        self, output="yaml",
    ):
        """Get the system and user locks.

        :param output: how to display the output ['yaml'|'json']
        """
        if output not in ["yaml", "json"]:
            print(
                "'output' parameter must be 'yaml' or 'json'", file=sys.stderr
            )
            sys.exit(1)

        response = base.get_client().lock.get()

        if output == "yaml":
            print(
                yaml.dump(
                    yaml.load(json.dumps(response), Loader=yaml.FullLoader,)
                )
            )
        else:
            print(json.dumps(response))

    @intercept_exception
    def create(
        self, reason,
    ):
        """Create a lock."""
        print(base.get_client().lock.create(reason), file=sys.stdout)

    @intercept_exception
    def delete(
        self, id,
    ):
        """Delete a user lock."""
        base.get_client().lock.delete(id)

    @intercept_exception
    def delete_all(
        self, timeout_secs=300,
    ):
        """Delete all locks."""
        success = base.get_client().lock.delete_all(timeout_secs=timeout_secs)
        if not success:
            print("Could not delete locks.", file=sys.stderr)
            sys.exit(1)


class LicenseProxy(object):
    """Proxy object to :py:attr:`<hpecp.client.license>`."""

    def __dir__(self):
        """Return the CLI method names."""
        return ["delete", "delete_all", "list", "platform_id", "register"]

    @intercept_exception
    def platform_id(self,):
        """Get the platform ID."""
        print(base.get_client().license.platform_id())

    def list(
        self, output="yaml", license_key_only=False,
    ):
        """Retrieve the list of licenses.

        :param output: how to display the output ['yaml'|'json']
        """
        response = base.get_client().license.list()
        if license_key_only:
            response = [
                str(unicode(li["LicenseKey"])) for li in response["Licenses"]
            ]
            print("\n".join(response))
        else:
            if output == "yaml":
                print(
                    yaml.dump(
                        yaml.load(
                            json.dumps(response), Loader=yaml.FullLoader,
                        )
                    )
                )
            else:
                print(json.dumps(response))

    @intercept_exception
    def register(
        self, server_filename,
    ):
        """Register a license.

        :param server_filename: Filepath to the license on the server, e.g.
            '/srv/bluedata/license/LICENSE-1.txt'
        """
        print(
            base.get_client().license.register(server_filename=server_filename)
        )

    # TODO implement me!
    # def upload_with_ssh_key(
    #     self,
    #     server_filename,
    #     ssh_key_file=None,
    #     ssh_key_data=None,
    #     license_file=None,
    #     base64enc_license_data=None,
    # ):
    #     """Not implemented yet.

    #     Workaround:
    #     -----------
    #      - scp your license to '/srv/bluedata/license/' on the controller
    #      - run client.license.register(server_filename) to register
    #        the license
    #     """
    #     raise Exception(
    #         "Not implemented yet! Workaround: scp your license to"
    #         "'/srv/bluedata/license/'"
    #     )

    # TODO implement me!
    # def upload_with_ssh_pass(
    #     self,
    #     server_filename,
    #     ssh_username,
    #     ssh_password,
    #     license_file=None,
    #     base64enc_license_data=None,
    # ):
    #     """Not implemented yet.

    #     Workaround:
    #     -----------
    #      - scp your license to '/srv/bluedata/license/' on the controller
    #      - run client.license.register(server_filename) to register
    #        the license
    #     """
    #     raise Exception(
    #         "Not implemented yet! Workaround: scp your license to"
    #         "'/srv/bluedata/license/'"
    #     )

    @intercept_exception
    def delete(
        self, license_key,
    ):
        """Delete a license by LicenseKey.

        :param license_key: The license key, e.g. '1234 1234 ... 1234
            "SOMETEXT"'
        """
        base.get_client().license.delete(license_key=license_key)

    @intercept_exception
    def delete_all(self,):
        """Delete all licenses."""
        response = base.get_client().license.list()
        all_license_keys = [
            str(unicode(li["LicenseKey"])) for li in response["Licenses"]
        ]
        for licence_key in all_license_keys:
            base.get_client().license.delete(license_key=licence_key)


class HttpClientProxy(object):
    """Proxy object to :py:attr:`<hpecp.client._request>`."""

    def __dir__(self):
        """Return the CLI method names."""
        return ["delete", "get", "post", "put"]

    @intercept_exception
    def get(
        self, url,
    ):
        """Make HTTP GET request.

        Examples
        --------
        $ hpecp httpclient get /api/v1/workers
        """
        response = base.get_client()._request(
            url, http_method="get", description="CLI HTTP GET",
        )
        print(response.text, file=sys.stdout)

    @intercept_exception
    def delete(
        self, url,
    ):
        """Make HTTP DELETE request.

        Examples
        --------
        $ hpecp httpclient delete /api/v1/workers/1
        """
        base.get_client()._request(
            url, http_method="delete", description="CLI HTTP DELETE",
        )

    @intercept_exception
    def post(
        self, url, json_file="",
    ):
        """Make HTTP POST request.

        Examples
        --------
        $ cat > my.json <<-EOF
            {
                "external_identity_server":  {
                    "bind_pwd":"5ambaPwd@",
                    "user_attribute":"sAMAccountName",
                    "bind_type":"search_bind",
                    "bind_dn":"cn=Administrator,CN=Users,DC=samdom,DC=example,DC=com",
                    "host":"10.1.0.77",
                    "security_protocol":"ldaps",
                    "base_dn":"CN=Users,DC=samdom,DC=example,DC=com",
                    "verify_peer": false,
                    "type":"Active Directory",
                    "port":636
                }
            }
            EOF

            hpecp httpclient post /api/v2/config/auth --json-file my.json
        """
        with open(json_file, "r",) as f:
            data = json.load(f)

        response = base.get_client()._request(
            url, http_method="post", data=data, description="CLI HTTP POST",
        )
        print(response.text, file=sys.stdout)

    @intercept_exception
    def put(
        self, url, json_file="",
    ):
        """Make HTTP PUT request.

        Examples
        --------
        $ hpecp httpclient put /api/v2/config/auth --json-file my.json
        """  # noqa: W293
        with open(json_file, "r",) as f:
            data = json.load(f)

        response = base.get_client()._request(
            url, http_method="put", data=data, description="CLI HTTP PUT",
        )
        print(response.text, file=sys.stdout)


class UserProxy(base.BaseProxy):
    """Proxy object to :py:attr:`<hpecp.client.user>`."""

    def __dir__(self):
        """Return the CLI method names."""
        return ["create", "get", "delete", "examples", "list"]

    def __init__(self):
        """Create instance of proxy class with the client module name."""
        super(UserProxy, self).new_instance("user", User)

    @intercept_exception
    def create(
        self, name, password, description, is_external=False,
    ):
        """Create a User.

        :param name: the user name
        :param password:  the password
        :param description: the user descripton

        """
        user_id = base.get_client().user.create(
            name=name,
            password=password,
            description=description,
            is_external=is_external,
        )
        print(user_id)

    def examples(self):
        """Show usage_examples of the list method."""
        print(
            dedent(
                """\

                hpecp user list --query '[?is_external]' --output json-pp
                """  # noqa: E501
            )
        )


class RoleProxy(base.BaseProxy):
    """Proxy object to :py:attr:`<hpecp.client.role>`."""

    def __dir__(self):
        """Return the CLI method names."""
        return ["delete", "examples", "get", "list"]

    def __init__(self):
        """Create instance of proxy class with the client module name."""
        super(RoleProxy, self).new_instance("role", Role)

    def examples(self):
        """Show examples for working with roles."""
        print(
            dedent(
                """\
                    
                # Retrieve the role ID for 'Admin'
                $ hpecp role list  --query "[?label.name == 'Admin'][_links.self.href] | [0][0]" --output json | tr -d '"'
                /api/v1/role/2
                """  # noqa:  E501
            )
        )


def configure_cli():
    """Configure the CLI."""
    controller_api_host = None
    controller_api_port = None
    controller_use_ssl = None
    controller_verify_ssl = None
    controller_warn_ssl = None
    controller_username = None
    controller_password = None

    config_path = os.path.join(os.path.expanduser("~"), ".hpecp.conf",)

    if os.path.exists(config_path):
        config_reader = ContainerPlatformClient.create_from_config_file()
        controller_api_host = config_reader.api_host
        controller_api_port = config_reader.api_port
        controller_use_ssl = config_reader.use_ssl
        controller_verify_ssl = config_reader.verify_ssl
        controller_warn_ssl = config_reader.warn_ssl
        controller_username = config_reader.username
        controller_password = config_reader.password

    sys.stdout.write("Controller API Host [{}]: ".format(controller_api_host))
    tmp = six.moves.input()
    if tmp != "":
        controller_api_host = tmp

    sys.stdout.write("Controller API Port [{}]: ".format(controller_api_port))
    tmp = six.moves.input()
    if tmp != "":
        controller_api_port = tmp

    sys.stdout.write(
        "Controller uses ssl (True|False) [{}]: ".format(controller_use_ssl)
    )
    tmp = six.moves.input()
    if tmp != "":
        controller_use_ssl = tmp

    sys.stdout.write(
        "Controller verify ssl (True|False) [{}]: ".format(
            controller_verify_ssl
        )
    )
    tmp = six.moves.input()
    if tmp != "":
        controller_verify_ssl = tmp

    sys.stdout.write(
        "Controller warn ssl (True|False) [{}]: ".format(controller_warn_ssl)
    )
    tmp = six.moves.input()
    if tmp != "":
        controller_warn_ssl = tmp

    sys.stdout.write("Controller Username [{}]: ".format(controller_username))
    tmp = six.moves.input()
    if tmp != "":
        controller_username = tmp

    sys.stdout.write("Controller Password [{}]: ".format(controller_password))
    tmp = six.moves.input()
    if tmp != "":
        controller_password = tmp

    config = configparser.ConfigParser()
    config["default"] = OrderedDict()
    config["default"]["api_host"] = controller_api_host
    config["default"]["api_port"] = str(controller_api_port)
    config["default"]["use_ssl"] = str(controller_use_ssl)
    config["default"]["verify_ssl"] = str(controller_verify_ssl)
    config["default"]["warn_ssl"] = str(controller_warn_ssl)
    config["default"]["username"] = controller_username
    config["default"]["password"] = controller_password

    with open(config_path, "w") as config_file:
        config.write(config_file)


class AutoComplete:
    """Shell autocompletion scripts.

    Example Usage:

    hpecp autocomplete bash > hpecp-bash.sh && source hpecp-bash.sh
    """

    def __dir__(self):
        """Return the CLI method names."""
        return ["bash"]

    def __init__(self, cli):
        """Create AutoCompletion class instance.

        Parameters
        ----------
        cli : CLI
            the owning cli instance
        """
        self.cli = cli

    def _get_metadata(self):

        modules = collections.OrderedDict()
        columns = collections.OrderedDict()

        for module_name in self.cli.__dict__.keys():

            # we manually define autocomplete for these methods
            if module_name in ["autocomplete", "configure_cli", "version"]:
                continue

            module = getattr(self.cli, module_name)
            function_names = dir(module)

            try:
                all_fields = getattr(module.resource_class, "all_fields")
            except Exception:
                all_fields = []

            function_parameters = collections.OrderedDict()

            # autcomplete should have most specific name first, e.g.
            # hpecp.tenant.create_xyz  before
            # hpecp.tenant.create
            for function_name in reversed(function_names):
                function = getattr(module, function_name)

                if six.PY2:
                    parameter_names = list(inspect.getargspec(function).args)
                else:
                    parameter_names = list(
                        inspect.getfullargspec(function).args
                    )

                # parameter_names = list(function.__code__.co_varnames)
                if "self" in parameter_names:
                    parameter_names.remove("self")

                # prefix parameter names with '--'
                parameter_names = list(map("--".__add__, parameter_names))

                function_parameters.update({function_name: parameter_names})

            modules[module_name] = function_parameters
            columns[module_name] = all_fields

            # _log.debug(modules)
            # _log.debug(columns)

        return (modules, columns)

    def bash(self,):
        """Create autocompletion script for bash."""
        __bash_template = dedent(
            """\
            _hpecp_complete()
                {
                local cur prev BASE_LEVEL

                COMPREPLY=()
                cur=${COMP_WORDS[COMP_CWORD]}
                prev=${COMP_WORDS[COMP_CWORD-1]}

                MODULE=${COMP_WORDS[1]}

                COMP_WORDS_AS_STRING=$(IFS=. ; echo "${COMP_WORDS[*]}")

                # if last input was > for redirecting to a file
                # perform file and directory autocompletion
                if echo "${prev}" | grep -q '>'
                then
                    _filedir;
                    return
                fi

                # from: https://stackoverflow.com/a/58221008/1033422

                declare -A MODULE_COLUMNS=(
                    {% for module_name in modules %}
                        {% set column_names = " ".join(columns[module_name]) %}
                        ['{{module_name}}']="{{column_names}}"
                    {% endfor %}
                )

                {% raw %}
                # list has uniform behaviour as it is implemented in base.BaseProxy
                if [[ "${COMP_WORDS[2]}" == "list" ]];
                then

                    # if 'list' was the last word
                    if [[ "${prev}" == "list" ]];
                    then
                        COMPREPLY=( $(compgen -W "--columns --query" -- $cur) )
                        return
                    fi

                    # FIXME: https://unix.stackexchange.com/questions/124539/bash-completion-for-comma-separated-values

                    # '--columns' was the last word and user is entering column names
                    if [[ "${COMP_WORDS[3]}" == "--columns"* && ${#COMP_WORDS[@]} -le 5 ]];
                    then
                        declare -a COLUMNS=(${MODULE_COLUMNS[$MODULE]})

                        local realcur prefix
                        realcur=${cur##*,} # everything after the last comma, e.g. a,b,c,d -> d
                        prefix=${cur%,*}   # everything before the lat comma, e.g. a,b,c,d -> a,b,c

                        if [[ "$cur" == *,* ]];
                        then
                            IFS=',' ENTERED_COLUMNS_LIST=($prefix)
                            unset IFS
                        else
                            IFS=',' ENTERED_COLUMNS_LIST=($prev)
                            unset IFS
                        fi

                        for COLUMN in ${COLUMNS[@]}; do
                            for ENTERED_COLUMN in ${ENTERED_COLUMNS_LIST[@]}; do
                                if [[ "${ENTERED_COLUMN}" == "${COLUMN}" ]]
                                then
                                    # remove columns already entered by user
                                    COLUMNS=(${COLUMNS[*]//$ENTERED_COLUMN/})
                                fi
                            done
                        done

                        if [[ "$cur" == *,* ]];
                        then
                            COMPREPLY=( $(compgen -W "${COLUMNS[*]}" -P "${prefix}," -S "," -- ${realcur}) )
                            compopt -o nospace
                            return
                        else
                            COMPREPLY=( $(compgen -W "${COLUMNS[*]}" -S "," -- ${realcur}) )
                            compopt -o nospace
                            return
                        fi
                    fi

                    # user has finished entering column list or query
                    if [[ ${#COMP_WORDS[@]} == 6 ]];
                    then
                        COMPREPLY=( $(compgen -W "--output" -- $cur) )
                        return
                    fi

                    if [[ "${COMP_WORDS[5]}" == "--output"*  ]];
                    then
                        if [[ "${COMP_WORDS[3]}" == "--columns"*  ]];
                        then
                            COMPREPLY=( $(compgen -W "table text" -- $cur) )
                            return
                        else
                            COMPREPLY=( $(compgen -W "json json-pp text" -- $cur) )
                            return
                        fi
                    fi

                    return
                fi
                {% endraw %}

                # if the last parameter was --*file perform
                # file and directory autocompletion
                if echo "${prev}" | grep -q '\-\-.*file$'
                then
                    _filedir;
                    return
                fi

                # if last input was > for redirecting to a file
                # perform file and directory autocompletion
                if echo "${prev}" | grep -q '>'
                then
                    _filedir;
                    return
                fi

                case "$COMP_WORDS_AS_STRING" in

                {% set module_names = " ".join(modules.keys()) %}
                {% for module_name in modules %}
                    {% set function_names = " ".join(modules[module_name].keys()).replace('_', '-') %}
                    {% for function_name in modules[module_name] %}
                        {% set param_names = " ".join(modules[module_name][function_name]).replace('_', '-') %}
                        {% if function_name == "list" %}
                            # do nothing - already handled above
                        {% else %}
                    *"hpecp.{{module_name}}.{{function_name.replace('_', '-')}}."*)
                        PARAM_NAMES="{{param_names}}"
                        for PARAM in ${PARAM_NAMES[@]}; do
                            PARAM="${PARAM//'\'}"
                            for WORD in ${COMP_WORDS[@]}; do
                                if [[ "${WORD}" == "${PARAM}" ]]
                                then
                                    # remove parameters already entered by user
                                    PARAM_NAMES=${PARAM_NAMES//$WORD/}
                                fi
                            done
                        done
                        COMPREPLY=( $(compgen -W "$PARAM_NAMES" -- $cur) )
                        ;;
                        {% endif %}
                    {% endfor %}
                    *"hpecp.{{module_name}}"*)
                        COMPREPLY=( $(compgen -W "{{function_names}}" -- $cur) )
                        ;;
                {% endfor %}
                    *"hpecp.autocomplete.bash"*)
                        COMPREPLY=( )
                        ;;
                    *"hpecp.autocomplete"*)
                        COMPREPLY=( $(compgen -W "bash" -- $cur) )
                        ;;
                    *"hpecp"*)
                        COMPREPLY=( $(compgen -W "autocomplete configure-cli version {{module_names}}" -- $cur) )
                        ;;
                esac
                return 0
            } &&
            complete -F _hpecp_complete hpecp
        """  # noqa: E501,W605
        )

        (modules, columns) = self._get_metadata()

        print(
            Environment(trim_blocks=True, lstrip_blocks=True)
            .from_string(__bash_template)
            .render(modules=modules, columns=columns),
            file=sys.stdout,
        )


def version():
    """Display version information."""
    print(ContainerPlatformClient.version())


class CLI(object):
    """Command Line Interface for the HPE Container Platform."""

    def __dir__(self):
        """Return modules names."""
        return vars(self)

    def __init__(self,):
        """Create a CLI instance."""
        self.autocomplete = AutoComplete(self)
        self.configure_cli = configure_cli
        self.catalog = CatalogProxy()
        self.k8sworker = K8sWorkerProxy()
        self.k8scluster = K8sClusterProxy()
        self.tenant = TenantProxy()
        self.gateway = GatewayProxy()
        self.lock = LockProxy()
        self.license = LicenseProxy()
        self.httpclient = HttpClientProxy()
        self.user = UserProxy()
        self.role = RoleProxy()
        self.version = version


if __name__ == "__main__":
    fire.Fire(CLI)
