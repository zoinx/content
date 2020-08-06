import time
import requests

import demistomock as demisto
from CommonServerPython import *

# Disable insecure warnings
requests.packages.urllib3.disable_warnings()

DATE_FORMAT = '%Y-%m-%dT%H:%M:%SZ'


class Client(BaseClient):
    """
    Client for f5 RESTful API.
    Args:
          base_url (str): f5 server url.
          token (str): f5 user token.
          use_ssl (bool): specifies whether to verify the SSL certificate or not.
          use_proxy (bool): specifies if to use Demisto proxy settings.
    """

    def __init__(self, base_url: str, token: str, use_ssl: bool, use_proxy: bool, **kwargs):
        super().__init__(base_url, verify=use_ssl, proxy=use_proxy, **kwargs)
        self.headers = {'Content-Type': 'application/json',
                        'X-F5-Auth-Token': token}

    def get_policy_md5(self, policy_name: str):
        """
            Get an MD5 hash of a policy that can be accessed in the API.

            Args:
                policy_name(str): Name of the policy to get a hash for.

            Returns:
                str: MD5 hash of the policy (can also be called the policy ID).
        """
        response = self._http_request(method='GET', url_suffix='asm/policies',
                                      headers=self.headers,
                                      params={'items': [{'name': policy_name}]})
        index = -1
        for element in response.get('items'):
            if element.get('name') == policy_name:
                index = response.get('items').index(element)
        response = (response.get('items')[index].get('plainTextProfileReference').get('link'))
        if index == -1:
            return policy_name
        return response.partition('policies/')[2].partition('/')[0]

    def get_id(self, md5: str, method_name: str, action: str):
        """
            Get the ID of a specific element (similar to getting the ID of the policy).

            Args:
                md5(str): MD5 hash of the policy the element is a member of.
                method_name(str): Name of the element the ID is from.
                action(str): endpoint where the element resides.

            Returns:
                str: MD5 hash (can also be called ID) of the element.
        """
        response = self._http_request(method='GET', url_suffix=f'asm/policies/{md5}/{action}',
                                      headers=self.headers, params={})
        index = -1
        for element in response.get('items'):
            if element.get('name') == method_name:
                index = response.get('items').index(element)
        if index == -1:
            return method_name
        return (response.get('items')[index]).get('id')

    def get_blocking_settings_id(self, md5: str, category: str, description: str):
        """
            Same as get_id, but for elements inside blocking_settings.

            Args:
                md5(str): MD5
                category(str): Category that the specific setting is in.
                description(str): Description of the policy (used like name).

            Returns:
                str: ID of the specific element, ready to be used for reference.
        """
        response = self._http_request(method='GET', url_suffix=f'asm/policies/'
                                                               f'{md5}/blocking-settings'
                                                               f'/{category}',
                                      headers=self.headers, params={})
        index = -1
        for element in response.get('items'):
            if element.get('description') == description:
                index = response.get('items').index(element)
        if index == -1:
            return description
        return (response.get('items')[index]).get('id')

    def get_ip_id(self, md5: str, ip_address: str):
        """
            Same as get_id, but for elements inside /whitelist_ips/.

            Args:
                md5(str): MD5
                ip_address(str): IP address (used like name)

            Returns:
                str: ID of the specific IP, ready to be used for reference.
                """
        response = self._http_request(method='GET', url_suffix=f'asm/policies/{md5}/whitelist-ips',
                                      headers=self.headers, params={})
        index = -1
        for element in response.get('items'):
            if element.get('ipAddress') == ip_address:
                index = response.get('items').index(element)
        if index == -1:
            return ip_address
        return (response.get('items')[index]).get('id')

    def get_policy_self_link(self, policy_name):
        response = self._http_request(method='GET', url_suffix='asm/policies',
                                      headers=self.headers,
                                      params={'items': [{'name': policy_name}]})

        return response.get('selfLink')

    def f5_list_policies_command(self, self_link: str = "", kind: str = "", items=None):
        """
        Lists all policies in the current server.

        Args:
            self_link(str): A link to this resource.
            kind(str): A unique type identifier.
            items(list): items

        Returns:
            response dictionary
        """
        if items is None:
            items = []
        response = self._http_request(method='GET', url_suffix='asm/policies',
                                      headers=self.headers, params={"selfLink": self_link,
                                                                    "kind": kind, "items": items})
        return format_list_policies(response)

    def f5_apply_policy_command(self, policy_reference_link):
        """
        Lists all policies in the current server.

        Args:
            policy_reference_link(str): link to the policy the user wish to apply.
        """
        body = {'policyReference': {'link': policy_reference_link}}
        response = self._http_request(method='POST', url_suffix='asm/tasks/apply-policy',
                                      headers=self.headers, json_data=body)
        return format_apply_policy(response)

    def f5_export_policy_command(self, filename: str, minimal: bool,
                                 policy_reference_link: str):

        """
        Export a policy.

        Args:
            filename(str): name of the file to export to.
            policy_reference_link(str): link to policy user wishes to export
            minimal(bool):Indicates whether to export only custom settings.
        """
        body = {'filename': filename, 'minimal': minimal,
                'policyReference': {'link': policy_reference_link}}
        response = self._http_request(method='POST', url_suffix='asm/tasks/export-policy',
                                      headers=self.headers, json_data=body)
        return format_export_policy(response)

    def f5_delete_policy_command(self, policy_name):
        """
        Delete a policy.

        Args:
            policy_name(str): The policy name.
        """

        md5 = self.get_policy_md5(policy_name)
        response = self._http_request(method='DELETE', url_suffix=f'asm/policies/{md5}',
                                      headers=self.headers, json_data={})
        return format_delete_policy(response)

    def f5_list_policy_methods_command(self, policy_name: str):
        """
        get all policy methods.

        Args:
            policy_name(str): The policy name

        Returns:
            dict: the report from f5.
        """
        md5_hash = self.get_policy_md5(policy_name)
        response = self._http_request(method='GET', headers=self.headers, json_data={},
                                      url_suffix=f'asm/policies/{md5_hash}/methods')
        return format_list_policy_methods(response)

    def f5_add_policy_methods_command(self, policy_name: str, new_method_name: str,
                                      act_as_method: str):
        """
        Add allowed method to a certain policy.

        Args:
            policy_name(str): The policy name.
            new_method_name(str): Display name of the new method.
            act_as_method(str): functionality of the new method. default is GET.
        """

        md5_hash = self.get_policy_md5(policy_name)
        body = {'name': new_method_name, 'actAsMethod': act_as_method.upper()}
        response = self._http_request(method='POST', headers=self.headers, json_data=body,
                                      url_suffix=f'asm/policies/{md5_hash}/methods')
        return format_policy_methods_command(response)

    def f5_update_policy_methods_command(self, policy_name: str, method_name: str,
                                         act_as_method: str):
        """
        Update allowed method from a certain policy..

        Args:
            policy_name(str): The policy name.
            method_name(str): Display name of the method.
            act_as_method(str): functionality of the new method.
        """
        md5_hash = self.get_policy_md5(policy_name)
        method_id = self.get_id(md5_hash, method_name, 'methods')
        body = {'name': method_name, 'actAsMethod': act_as_method.upper()}

        response = self._http_request(method='PATCH', headers=self.headers, json_data=body,
                                      url_suffix=f'asm/policies/{md5_hash}/methods/{method_id}')
        return format_policy_methods_command(response)

    def f5_delete_policy_methods_command(self, policy_name: str, method_name: str):
        """
        Add allowed method to a certain policy.

        Args:
            policy_name(str): The policy name.
            method_name(str): Display name of the method.
        """

        md5_hash = self.get_policy_md5(policy_name)
        method_id = self.get_id(md5_hash, method_name, 'methods')
        response = self._http_request(method='DELETE', headers=self.headers, json_data={},
                                      url_suffix=f'asm/policies/{md5_hash}/methods/{method_id}')
        return format_policy_methods_command(response)

    def f5_list_policy_file_types_command(self, policy_name: str):
        """
        Lists the file types that are allowed or disallowed in the security policy.

        Args:
            policy_name(str): The policy name
        """
        md5_hash = self.get_policy_md5(policy_name)
        response = self._http_request(method='GET', headers=self.headers, json_data={},
                                      url_suffix=f'asm/policies/{md5_hash}/filetypes')
        return format_list_policy_file_type(response)

    def f5_add_policy_file_types_command(self, policy_name: str, new_file_type: str,
                                         query_string_length: int,
                                         check_post_data_length: bool, response_check: bool,
                                         check_request_length: bool, post_data_length: int,
                                         perform_staging: bool):
        """
        Add allowed file types to a certain policy.

        Args:
            policy_name(str): The policy name.
            new_file_type(str): The new file type to add.
            query_string_length(int): Query string length. default is 100.
            check_post_data_length(bool): indicates if the user wishes check the length of
                                            data in post method. default is True.
            response_check(bool): Indicates if the user wishes to check the response.
            check_request_length(bool): Indicates if the user wishes to check the request length.
            post_data_length(int): post data length.
            perform_staging(bool): Indicates if the user wishes the new file type to be at staging.
        """
        md5_hash = self.get_policy_md5(policy_name)
        body = {'name': new_file_type,
                'queryStringLength': query_string_length,
                'checkPostDataLength': check_post_data_length,
                'responseCheck': response_check,
                'checkRequestLength': check_request_length,
                'postDataLength': post_data_length,
                'performStaging': perform_staging}

        response = self._http_request(method='POST', headers=self.headers, json_data=body,
                                      url_suffix=f'asm/policies/{md5_hash}/filetypes')
        return format_file_type_command(response)

    def f5_update_policy_file_types_command(self, policy_name: str, file_type_name: str,
                                            query_string_length: int,
                                            check_post_data_length: bool, response_check: bool,
                                            check_request_length: bool, post_data_length: int,
                                            perform_staging: bool):
        """
        Update a given file type from a certain policy.

        Args:
            policy_name(str): The policy name.
            file_type_name(str): The new file type to add.
            query_string_length(int): Query string length. default is 100.
            check_post_data_length(bool): indicates if the user wishes check the length of
                                            data in post method. default is True.
            response_check(bool): Indicates if the user wishes to check the response.
            check_request_length(bool): Indicates if the user wishes to check the request length.
            post_data_length(int): post data length.
            perform_staging(bool): Indicates if the user wishes the new file type to be at staging.
        """
        md5 = self.get_policy_md5(policy_name)
        file_type_id = self.get_id(md5, file_type_name, 'filetypes')

        body = {'name': file_type_name,
                'queryStringLength': query_string_length,
                'checkPostDataLength': check_post_data_length,
                'responseCheck': response_check,
                'checkRequestLength': check_request_length,
                'postDataLength': post_data_length,
                'performStaging': perform_staging}

        response = self._http_request(method='PATCH', headers=self.headers, json_data=body,
                                      url_suffix=f'asm/policies/{md5}/filetypes/{file_type_id}')
        return format_file_type_command(response)

    def f5_delete_policy_file_types_command(self, policy_name: str, file_type_name: str):
        """
        Add allowed method to a certain policy.

        Args:
            policy_name(str): The policy name.
            file_type_name(str): The new file type to delete.
        """
        md5 = self.get_policy_md5(policy_name)
        file_type_id = self.get_id(md5, file_type_name, 'filetypes')
        response = self._http_request(method='DELETE', headers=self.headers, json_data={},
                                      url_suffix=f'asm/policies/{md5}/filetypes/{file_type_id}')
        return format_file_type_command(response)

    def f5_list_policy_hostname_command(self, policy_name: str):
        """
            List all hostnames from a selected policy.

            Args:
                policy_name(str): The policy name to get hostnames from.
        """
        md5 = self.get_policy_md5(policy_name)
        response = self._http_request(method='GET', headers=self.headers, json_data={},
                                      url_suffix=f'asm/policies/{md5}/host-names')
        return format_policy_hostnames_command(response)

    def f5_add_policy_hostname_command(self, policy_name: str, name: str,
                                       include_subdomains: bool):
        """
            Add a hostname to a selected policy.

            Args:
                policy_name(str): The policy name to add the hostname to.
                name(str): Host name to add.
                include_subdomains(bool): Choice (true/false) whether or not to include subdomains.
        """
        md5 = self.get_policy_md5(policy_name)
        response = self._http_request(method='POST', headers=self.headers,
                                      json_data={'name': name,
                                                 'includeSubdomains': include_subdomains},
                                      url_suffix=f'asm/policies/{md5}/host-names')
        return format_policy_hostname_command(response)

    def f5_update_policy_hostname_command(self, policy_name: str, name: str,
                                          include_subdomains: bool):
        """
            Update a hostname in a selected policy.

            Args:
                policy_name(str): The policy name to update the hostname in.
                name(str): Host name to update.
                include_subdomains(bool): Choice (true/false) whether or not to include subdomains.
        """
        md5 = self.get_policy_md5(policy_name)
        hostname_id = self.get_id(md5, name, 'host-names')
        response = self._http_request(method='PATCH', headers=self.headers,
                                      json_data={'includeSubdomains': include_subdomains},
                                      url_suffix=f'asm/policies/{md5}/host-names/{hostname_id}')
        return format_policy_hostname_command(response)

    def f5_delete_policy_hostname_command(self, policy_name: str, name: str):
        """
            Delete a hostname from a selected policy.

            Args:
                policy_name(str): The policy name to delete the hostname from.
                name(str): Host name to delete.
        """
        md5 = self.get_policy_md5(policy_name)
        hostname_id = self.get_id(md5, name, 'host-names')
        response = self._http_request(method='DELETE', headers=self.headers,
                                      url_suffix=f'asm/policies/{md5}/host-names/{hostname_id}')
        return format_policy_hostname_command(response)

    def f5_list_policy_blocking_settings_command(self, policy_name: str, endpoint: str):
        """
            List a Blocking Settings element of a selected policy.

            Args:
                policy_name(str): Name of the policy the BS is in.
                endpoint(str): Sub-path of the wanted BS endpoint.
        """
        md5 = self.get_policy_md5(policy_name)
        response = self._http_request(method='GET', headers=self.headers,
                                      url_suffix=f'asm/policies/{md5}/blocking-settings/{endpoint}')
        return format_policy_blocking_settings_list_command(response, endpoint)

    def f5_update_policy_blocking_settings_command(self, policy_name: str, endpoint: str,
                                                   description: str, enabled=None, learn=True,
                                                   alarm=None, block=None):
        """
            Update a specific BS element of a certain policy.

            Args:
                policy_name(str): Name of the policy the BS is in.
                endpoint(str): Sub-path of the wanted BS endpoint.
                description(str): Since there is no name, use description instead.
                enabled(bool): If possible, enable the element.
                learn(bool): If possible, have the element learn.
                alarm(bool): If possible, have the element alarm.
                block(bool): If possible, have the element block.
        """
        md5 = self.get_policy_md5(policy_name)
        print(md5)
        blocking_settings_id = self.get_blocking_settings_id(md5, endpoint, description)
        json_body_start = {'enabled': enabled, 'learn': learn, 'alarm': alarm, 'block': block}

        body = {}

        for pair in json_body_start.items():
            if pair[1] is not None:
                body.update({pair[0]: pair[1]})

        print(body)
        url_suffix = f'asm/policies/{md5}/blocking-settings/{endpoint}/{blocking_settings_id}'
        response = self._http_request(method='PATCH', headers=self.headers,
                                      url_suffix=url_suffix, json_data=body)
        return format_policy_blocking_settings_single_command(response, endpoint)

    def f5_list_policy_urls_command(self, policy_name: str):
        """
            Get a list of all URLs of a policy.

            Args:
                policy_name(str): Name of the policy to retrieve.
        """
        md5 = self.get_policy_md5(policy_name)
        response = self._http_request(method='GET', headers=self.headers, json_data={},
                                      url_suffix=f'asm/policies/{md5}/urls')
        return format_list_policy_urls_command(response)

    def f5_add_policy_url_command(self, policy_name: str, name: str, method: str, protocol: str,
                                  url_type: str, description: str = '', is_allowed=True):
        """
            Create a new URL in a selected policy.

            Args:
                policy_name(str): Name of the policy to add a URL to.
                name(str): Name of the new URL.
                method(str): Method to be used in the.
                protocol(str): HTTP or HTTPS
                description(str): Optional descrption for the URL.
                url_type(str): Explicit or wildcard.
                is_allowed(str): Whether or not the URL is allowed
        """
        md5 = self.get_policy_md5(policy_name)
        json_body = {'name': name, 'protocol': protocol, 'description': description,
                     'method': method, 'type': url_type, 'isAllowed': is_allowed}
        response = self._http_request(method='POST', headers=self.headers, json_data=json_body,
                                      url_suffix=f'asm/policies/{md5}/urls')
        return format_policy_url_command(response)

    def f5_update_policy_url_command(self, policy_name: str, name: str, perform_staging=None,
                                     description=None, mandatory_body=None,
                                     clickjacking_protection=None, url_isreferrer=None):
        """
            Update an existing URL in a policy.

            Args:
                policy_name(str): Name of the policy to add a URL to.
                name(str): Name of the URL to update.
                perform_staging(str): Whether or not to stage the URL.
                description(str): Optional new description.
                mandatory_body(str): Whether or not the body is mandatory
                clickjacking_protection(str): Whether or not to enable clickjacking protection
                url_isreferrer(str): Whether or not the URL is a referrer.
        """
        md5 = self.get_policy_md5(policy_name)
        url_id = self.get_id(md5, name, 'urls')
        json_body_start = {'performStaging': perform_staging, 'description': description,
                           'mandatoryBody': mandatory_body,
                           'clickjackingProtection': clickjacking_protection,
                           'urlIsReferrer': url_isreferrer}
        json_body = {}
        for pair in json_body_start.items():
            if pair[1] is not None:
                json_body.update({pair[0]: pair[1]})

        response = self._http_request(method='PATCH', headers=self.headers, json_data=json_body,
                                      url_suffix=f'asm/policies/{md5}/urls/{url_id}')

        return format_policy_url_command(response)

    def f5_delete_policy_url_command(self, policy_name: str, name: str):
        """
            Delete an existing URL in a policy.

            Args:
                policy_name(str): Name of the policy to add a URL to.
                name(str): Name of the URL to delete.
        """
        md5 = self.get_policy_md5(policy_name)
        url_id = self.get_id(md5, name, 'urls')
        response = self._http_request(method='DELETE', headers=self.headers, json_data={},
                                      url_suffix=f'asm/policies/{md5}/urls/{url_id}')
        return format_policy_url_command(response)

    def f5_list_policy_cookies_command(self, policy_name: str):
        """
        Lists the file types that are allowed or disallowed in the security policy.

        Args:
            policy_name(str): The policy name
        """
        md5_hash = self.get_policy_md5(policy_name)
        response = self._http_request(method='GET', headers=self.headers, json_data={},
                                      url_suffix=f'asm/policies/{md5_hash}/cookies')
        return format_list_cookies(response)

    def f5_add_policy_cookies_command(self, policy_name: str, new_cookie_name: str,
                                      perform_staging: bool):
        """
        Add new cookie to a specific policy

        Args:
            policy_name(str): The policy name.
            new_cookie_name(str): The new cookie name to add.
            perform_staging(bool): Indicates if the user wishes the new file type to be at staging.
        """
        md5_hash = self.get_policy_md5(policy_name)
        body = {'name': new_cookie_name,
                'performStaging': perform_staging, }

        response = self._http_request(method='POST', headers=self.headers, json_data=body,
                                      url_suffix=f'asm/policies/{md5_hash}/cookies')
        return format_cookies_command(response, 'adding')

    def f5_update_policy_cookies_command(self, policy_name: str, cookie_name: str,
                                         perform_staging: bool):
        """
        Update a given file type from a certain policy.

        Args:
            policy_name(str): The policy name.
            cookie_name(str): The cookie to update.
            perform_staging(bool): Indicates if the user wishes the new file type to be at staging.
        """

        md5_hash = self.get_policy_md5(policy_name)
        print(md5_hash)
        file_type_id = self.get_id(md5_hash, cookie_name, 'policy-cookies')

        body = {'name': cookie_name,
                'performStaging': perform_staging}

        response = self._http_request(method='PATCH', headers=self.headers, json_data=body,
                                      url_suffix=f'asm/policies/{md5_hash}/cookies/{file_type_id}')
        return format_cookies_command(response, 'updating')

    def f5_delete_policy_cookies_command(self, policy_name: str, cookie_name: str):
        """
        Add allowed method to a certain policy.

        Args:
            policy_name(str): The policy name.
            cookie_name(str): The cookie to delete.
        """

        md5 = self.get_policy_md5(policy_name)
        file_type_id = self.get_id(md5, cookie_name, 'cookies')
        response = self._http_request(method='DELETE', headers=self.headers, json_data={},
                                      url_suffix=f'asm/policies/{md5}/cookies/{file_type_id}')
        return format_cookies_command(response, 'deleting')

    def f5_list_policy_whitelist_ips_command(self, policy_name: str):
        """
            List all whitelisted IPs for a certain policy.

            Args:
                policy_name(str): Name of the policy to get IPs for.
        """

        md5_hash = self.get_policy_md5(policy_name)
        response = self._http_request(method='GET', headers=self.headers, json_data={},
                                      url_suffix=f'asm/policies/{md5_hash}/whitelist-ips')
        return format_policy_whitelist_ips_command(response)

    def f5_add_policy_whitelist_ips_command(self, policy_name: str, ip_address: str,
                                            ip_mask=None, trusted_by_builder=None,
                                            ignore_brute_detection=None,
                                            description=None, block_requests=None,
                                            ignore_learning=None, never_log=None,
                                            ignore_intelligence=None):
        """
            Create a new whitelisted IP for a certain policy.

            Args:
                policy_name(str): Name of the policy to add the IP to.
                ip_address(str): New IP address.
                ip_mask(str): Subnet mask for the new IP.
                trusted_by_builder(bool): Whether or not the IP is trusted by the policy builder.
                ignore_brute_detection(bool): Whether or not to ignore detections of brute force.
                description(str): Optional description for the new IP.
                block_requests(str): Method of blocking requests.
                ignore_learning(bool): Whether or not to ignore learning suggestions.
                never_log(bool): Whether or not to never log from the IP.
                ignore_intelligence(bool): Whether or not to ignore intelligence gathered on the IP.
        """
        md5_hash = self.get_policy_md5(policy_name)
        json_body_start = {'ipAddress': ip_address, 'ipMask': ip_mask,
                           'ignoreIpReputation': ignore_intelligence,
                           'blockRequests': block_requests,
                           'ignoreAnomalies': ignore_brute_detection, 'description': description,
                           'neverLearnRequests': ignore_learning, 'neverLogRequests': never_log,
                           'trustedByPolicyBuilder': trusted_by_builder}
        json_body = {}
        for pair in json_body_start.items():
            if pair[1] is not None:
                json_body.update({pair[0]: pair[1]})
        response = self._http_request(method='POST', headers=self.headers,
                                      url_suffix=f'asm/policies/{md5_hash}/whitelist-ips/',
                                      json_data=json_body)
        return format_policy_whitelist_ip_command(response, 'created')

    def f5_update_policy_whitelist_ips_command(self, policy_name: str, ip_address: str,
                                               trusted_by_builder=None,
                                               ignore_brute_detection=None,
                                               description=None, block_requests=None,
                                               ignore_learning=None, never_log=None,
                                               ignore_intelligence=None):
        """
            Update an existing whitelisted IP for a certain policy.

            Args:
                policy_name(str): Name of the policy to update the IP in.
                ip_address(str): IP address.
                trusted_by_builder(bool): Whether or not the IP is trusted by the policy builder.
                ignore_brute_detection(bool): Whether or not to ignore detections of brute force.
                description(str): Optional description for the new IP.
                block_requests(str): Method of blocking requests.
                ignore_learning(bool): Whether or not to ignore learning suggestions.
                never_log(bool): Whether or not to never log from the IP.
                ignore_intelligence(bool): Whether or not to ignore intelligence gathered on the IP.
        """
        md5_hash = self.get_policy_md5(policy_name)
        ip_id = self.get_ip_id(md5_hash, ip_address)
        json_body_start = {'ignoreIpReputation': ignore_intelligence,
                           'blockRequests': block_requests,
                           'ignoreAnomalies': ignore_brute_detection, 'description': description,
                           'neverLearnRequests': ignore_learning, 'neverLogRequests': never_log,
                           'trustedByPolicyBuilder': trusted_by_builder}
        json_body = {}
        for pair in json_body_start.items():
            if pair[1] is not None:
                json_body.update({pair[0]: pair[1]})
        response = self._http_request(method='PATCH', headers=self.headers,
                                      url_suffix=f'asm/policies/{md5_hash}/whitelist-ips/{ip_id}',
                                      json_data=json_body)
        return format_policy_whitelist_ip_command(response, 'updated')

    def f5_delete_policy_whitelist_ips_command(self, policy_name: str, ip_address: str):
        """
            Delete an existing whitelisted IP from a policy.

            Args:
                policy_name(str): Name of the policy to delete the IP from.
                ip_address(str): IP address.
        """
        md5_hash = self.get_policy_md5(policy_name)
        ip_id = self.get_ip_id(md5_hash, ip_address)
        response = self._http_request(method='DELETE', headers=self.headers, json_data={},
                                      url_suffix=f'asm/policies/{md5_hash}/whitelist-ips/{ip_id}')
        return format_policy_whitelist_ip_command(response, 'deleted')


def test_module(server_address, username, password, verify_certificate):
    """Returning 'ok' indicates that the integration works like it is supposed to."""
    response = requests.get(f'{server_address}sys/version', verify=verify_certificate,
                            auth=(username, password))
    if response.status_code == 200:
        return 'ok'
    if 400 <= response.status_code < 500:
        return f'Invalid credentials given.\nError: {response.status_code}: {response.text}'
    if response.status_code >= 500:
        return f'Invalid credentials given.\nError: {response.status_code}: {response.text}'
    return f'Error {response.status_code}: {response.text}'


def login(server_ip: str, username: str, password: str, verify_certificate: bool) -> str:
    """Log into the F5 instance in order to get a session token for further auth."""
    res = requests.post(f'https://{server_ip}/mgmt/shared/authn/login', verify=verify_certificate,
                        json={'username': username, 'password': password,
                              'loginProviderName': 'tmos'})
    return res.json().get('token').get('token')


def format_list_policies(result: dict):
    """
        Formats f5 policy list Demisto's outputs.

    Returns:
        str: the markdown to display inside Demisto.
        dict: the context to return into Demisto.
        dict: the report from f5 (used for debugging).
    """

    if not result:
        return 'No data to show.', {}, result

    result = result.get('items')
    if not result:
        return 'No data to show.', {}, result

    printable_result = []
    for item in result:
        current_object_data = {
            'name': item.get('name'),
            'id': item.get('id'),
            'type': item.get('type'),
            'creator-name': item.get('creatorName'),
            'created-time': item.get('createdDatetime'),
            'enforcement-mode': item.get('enforcementMode'),
            'active': item.get('active'),
        }
        printable_result.append(current_object_data)
    outputs = {'f5.ListPolicies(val.uid && val.uid == obj.uid)': printable_result}
    readable_output = tableToMarkdown('f5 data for listing policies:', printable_result,
                                      ['name', 'id', 'type', 'enforcement-mode',
                                       'creator-name', 'active', 'created-time'],
                                      removeNull=True)
    return readable_output, outputs, result


def format_apply_policy(result):
    """
        Formats f5 policy apply Demisto's outputs.

    Returns:
        str: the markdown to display inside Demisto.
        dict: the context to return into Demisto.
        dict: the report from f5 (used for debugging).
    """
    if not result:
        return 'No data to show.', {}, result

    outputs = {'f5.ApplyPolicy(val.uid && val.uid == obj.uid)': {
        'policy-reference': result.get('policyReference').get('link'),
        'status': result.get('status'),
        'id': result.get('id'),
        'start-time': result.get('startTime'),
        'kind': result.get('kind'),
    }}

    table_data = outputs['f5.ApplyPolicy(val.uid && val.uid == obj.uid)']
    readable_output = tableToMarkdown('f5 data for applying policy:', table_data,
                                      removeNull=True)
    return readable_output, outputs, result


def format_export_policy(result):
    """
        Formats f5 policy export Demisto's outputs.

    Returns:
        str: the markdown to display inside Demisto.
        dict: the context to return into Demisto.
        dict: the report from f5 (used for debugging).
    """

    if not result:
        return 'No data to show.', {}, result

    outputs = {'f5.ExportPolicy(val.uid && val.uid == obj.uid)': {
        'status': result.get('status'),
        'id': result.get('id'),
        'start-time': result.get('startTime'),
        'kind': result.get('kind'),
        'format': result.get('format'),
        'filename': result.get('filename'),
    }}
    policy_reference = result.get('policyReference')
    if policy_reference:
        outputs['policy-reference'] = policy_reference.get('link')

    table_data = outputs['f5.ExportPolicy(val.uid && val.uid == obj.uid)']
    readable_output = tableToMarkdown('f5 data for exporting policy:', table_data,
                                      removeNull=True)
    return readable_output, outputs, result


def format_delete_policy(result):
    """
        Formats f5 delete policy to Demisto's outputs.

    Args:
        result (dict): the report from f5.

    Returns:
        str: the markdown to display inside Demisto.
        dict: the context to return into Demisto.
        dict: the report from f5 (used for debugging).
    """
    if not result:
        return 'No data to show.', {}, result

    outputs = {'f5.delete-policy(val.uid && val.uid == obj.uid)': {
        'name': result.get('name'),
        'id': result.get('id'),
        'self-link': result.get('selfLink'),
    }}

    table_data = outputs['f5.delete-policy(val.uid && val.uid == obj.uid)']
    readable_output = tableToMarkdown('f5 data for deleting policy:', table_data,
                                      ['name', 'id', 'self-link'], removeNull=True)
    return readable_output, outputs, result


def format_list_policy_methods(result: dict):
    """
        Formats f5 policy methods to Demisto's outputs.

    Returns:
        str: the markdown to display inside Demisto.
        dict: the context to return into Demisto.
        dict: the report from f5 (used for debugging).
    """
    if not result:
        return 'No data to show.', {}, result
    result = result.get('items')
    if not result:
        return 'No data to show.', {}, result

    printable_result = []
    for item in result:
        current_object_data = {
            'name': item.get('name'),
            'act-as-method': item.get('actAsMethod'),
            'id': item.get('id'),
            'self-link': item.get('selfLink'),
            'kind': item.get('kind'),
            'last-updated': format_date(item.get('lastUpdateMicros')),
        }
        printable_result.append(current_object_data)

    outputs = {'f5.PolicyMethods(val.uid && val.uid == obj.uid)': printable_result}
    readable_output = tableToMarkdown('f5 data for listing all policy methods:', printable_result,
                                      ['name', 'act-as-method', 'id', 'self-link', 'kind',
                                       'last-updated'], removeNull=True)
    return readable_output, outputs, result


def format_list_policy_file_type(result: dict):
    """
        Formats f5 policy file type to Demisto's outputs.

    Args:
        result (dict): the report from f5.

    Returns:
        str: the markdown to display inside Demisto.
        dict: the context to return into Demisto.
        dict: the report from f5 (used for debugging).
    """
    if not result:
        return 'No data to show.', {}, result
    result = result.get('items')
    if not result:
        return 'No data to show.', {}, result

    printable_result = []
    for item in result:
        current_object_data = {
            'name': item.get('name'),
            'id': item.get('id'),
            'self-link': item.get('selfLink'),
            'query-string-length': item.get('queryStringLength'),
            'check-request-length': item.get('checkRequestLength'),
            'kind': item.get('kind'),
            'allowed': item.get('allowed'),
            'last-updated': format_date(item.get('lastUpdateMicros')),
        }
        printable_result.append(current_object_data)

    outputs = {'f5.FileTypes(val.uid && val.uid == obj.uid)': printable_result}
    readable_output = tableToMarkdown('Listing all f5 file type:', printable_result,
                                      ['name', 'id', 'self-link', 'query-string-length',
                                       'check-request-length',
                                       'kind', 'allowed', 'last-updated'], removeNull=True)

    return readable_output, outputs, result


def format_policy_methods_command(result: dict):
    """
        Formats f5 policy methods to Demisto's outputs.

    Args:
        result (dict): the report from f5.

    Returns:
        str: the markdown to display inside Demisto.
        dict: the context to return into Demisto.
        dict: the report from f5 (used for debugging).
    """
    if not result:
        return 'No data to show.', {}, result

    outputs = {'f5.PolicyMethods(val.uid && val.uid == obj.uid)': {
        'name': result.get('name'),
        'id': result.get('id'),
        'act-as-method': result.get('actAsMethod'),
        'self-link': result.get('selfLink'),
        'kind': result.get('kind'),
    }}

    table_data = outputs['f5.PolicyMethods(val.uid && val.uid == obj.uid)']
    readable_output = tableToMarkdown('f5 data for policy methods:',
                                      table_data, ['name', 'act-as-method', 'id', 'self-link',
                                                   'kind'], removeNull=True)
    return readable_output, outputs, result


def format_file_type_command(result: dict):
    """
        Formats f5 policy methods to Demisto's outputs.

    Args:
        result (dict): the report from f5.

    Returns:
        str: the markdown to display inside Demisto.
        dict: the context to return into Demisto.
        dict: the report from f5 (used for debugging).
    """

    if not result:
        return 'No data to show.', {}, result

    outputs = {'f5.FileType(val.uid && val.uid == obj.uid)': {
        'name': result.get('name'),
        'id': result.get('id'),
        'self-link': result.get('selfLink'),
        'query-string-length': result.get('queryStringLength'),
        'check-request-length': result.get('checkRequestLength'),
        'response-check': result.get('responseCheck'),
        'check-url-length': result.get('checkUrlLength'),
        'post-data-length': result.get('postDataLength'),
        'url-length': result.get('urlLength'),
        'perform-staging': result.get('performStaging'),
        'allowed': result.get('allowed'),
        'last-updated': format_date(result.get('lastUpdateMicros')),
    }}
    table_data = outputs['f5.FileType(val.uid && val.uid == obj.uid)']

    readable_output = tableToMarkdown('f5 data for file types:', table_data,
                                      ['name', 'id', 'self-link', 'query-string-length',
                                       'check-request-length',
                                       'response-check', 'check-url-length', 'url-length',
                                       'post-data-length',
                                       'perform-staging', 'allowed', 'last-updated'],
                                      removeNull=True)

    return readable_output, outputs, result


def format_policy_hostname_command(result: dict):
    """
            Formats f5 policy hostnames to Demisto's outputs.

        Args:
            result (dict): the report from f5.

        Returns:
            str: the markdown to display inside Demisto.
            dict: the context to return into Demisto.
            dict: the report from f5 (used for debugging).
        """
    if not result:
        return 'Nothing to show', {}, result
    printable_result = {
        'name': result.get('name'),
        'id': result.get('id'),
        'created-by': result.get('createdBy'),
        'self-link': result.get('selfLink'),
        'include-subdomains': result.get('includeSubdomains'),
        'last-update': format_date(result.get('lastUpdateMicros')),
    }
    outputs = {'f5.Hostname(val.uid && val.uid == obj.uid)': printable_result}
    readable_output = tableToMarkdown("f5 information about hosts", printable_result,
                                      headers=['id', 'name', 'created-by', 'include-subdomains',
                                               'kind', 'self-link', 'last-update'],
                                      removeNull=True)
    return readable_output, outputs, result


def format_policy_hostnames_command(result: dict):
    """
                Formats f5 policy hostname to Demisto's outputs.

            Args:
                result (dict): the report from f5.

            Returns:
                str: the markdown to display inside Demisto.
                dict: the context to return into Demisto.
                dict: the report from f5 (used for debugging).
            """
    entries = result.get('items')
    if not entries:
        return 'Nothing to show', {}, result
    printable_result = []
    for item in entries:
        current_object_data = {
            'name': item.get('name'),
            'id': item.get('id'),
            'created-by': item.get('createdBy'),
            'self-link': item.get('selfLink'),
            'include-subdomains': item.get('includeSubdomains'),
            'last-update': format_date(item.get('lastUpdateMicros')),
        }
        printable_result.append(current_object_data)
    outputs = {'f5.Hostname(val.uid && val.uid == obj.uid)': printable_result}
    readable_output = tableToMarkdown("f5 information about hosts", printable_result,
                                      headers=['id', 'name', 'created-by', 'include-subdomains',
                                               'kind', 'self-link', 'last-update'],
                                      removeNull=True)
    return readable_output, outputs, result


def format_policy_blocking_settings_list_command(result: dict, endpoint: str):
    """
        Format multiple BS (Blocking Setting) entries for demisto.
        Args:
            result(dict): API response from F5.
            endpoint(str): One of: evasions, violations, web-services-securities, http-protocols.

        Returns:
                str: the markdown to display inside Demisto.
                dict: the context to return into Demisto.
                dict: the report from f5 (used for debugging).
    """
    references = {'evasions': 'evasionReference', 'violations': 'violationReference',
                  'web-services-securities': 'webServicesSecurityReference',
                  'http-protocols': 'httpProtocolReference'}
    entries = result.get('items')
    if not entries:
        return 'Nothing to show', {}, result
    printable_result = []
    for item in entries:
        current_object_data = {
            'description': item.get('description'),
            'learn': item.get('learn'),
            'alarm': item.get('alarm'),
            'block': item.get('block'),
            'id': item.get('id'),
            'kind': item.get('kind'),
            'enabled': item.get('enabled'),
            'self-link': item.get('selfLink'),
            'section-reference': item.get('sectionReference').get('link') if item.get(
                'sectionReference') else None,
            'last-update': format_date(item.get('lastUpdateMicros')),
        }
        reference_link = item.get(references.get(endpoint))

        if reference_link:
            current_object_data['reference'] = reference_link.get('link')
        printable_result.append(current_object_data)

    outputs = {'f5.BlockingSettings(val.uid && val.uid == obj.uid)': printable_result}
    readable_output = tableToMarkdown(f'{endpoint.capitalize()} for selected policy',
                                      printable_result,
                                      headers=['id', 'description', 'enabled', 'learn', 'alarm',
                                               'block', 'kind', 'reference',
                                               'self-link', 'section-reference', 'last-update'],
                                      removeNull=True)
    return readable_output, outputs, result


def format_policy_blocking_settings_single_command(result: dict, endpoint: str):
    """
        Format a single BS (Blocking Setting) element for demisto.

        Args:
            result(dict): API response from F5.
            endpoint(str): One of: evasions, violations, web-services-securities, http-protocols.

        Returns:
                str: the markdown to display inside Demisto.
                dict: the context to return into Demisto.
                dict: the report from f5 (used for debugging).
    """
    references = {'evasions': 'evasionReference', 'violations': 'violationReference',
                  'web-services-securities': 'webServicesSecurityReference',
                  'http-protocols': 'httpProtocolReference'}
    printable_result = {
        'description': result.get('description'),
        'learn': result.get('learn'),
        'alarm': result.get('alarm'),
        'block': result.get('block'),
        'id': result.get('id'),
        'kind': result.get('kind'),
        'enabled': result.get('enabled'),
        'self-link': result.get('selfLink'),
        'last-update': format_date(result.get('lastUpdateMicros')),
    }
    section_reference = result.get('sectionReference')
    if section_reference:
        printable_result['section-reference'] = section_reference.get('link')

    reference_link = result.get(references.get(endpoint))
    if reference_link:
        printable_result['reference'] = reference_link.get('link')

    outputs = {'f5.BlockingSettings(val.uid && val.uid == obj.uid)': printable_result}
    readable_output = tableToMarkdown(f'Modified {endpoint}', printable_result,
                                      headers=['id', 'description', 'enabled', 'learn', 'alarm',
                                               'block', 'kind', 'reference', 'self-link',
                                               'section-reference', 'last-update'],
                                      removeNull=True)
    return readable_output, outputs, result


def format_list_policy_urls_command(result: dict):
    """
        Formats multiple resource URLs for demisto
        Args:
            result(dict): API response from F5.

        Returns:
                str: the markdown to display inside Demisto.
                dict: the context to return into Demisto.
                dict: the report from f5 (used for debugging).
    """
    entries = result.get('items')
    if not entries:
        return 'Nothing to show', {}, result
    printable_result = []
    for item in entries:
        current_object = {'id': item.get('id'), 'name': item.get('name'),
                          'description': item.get('description'), 'protocol': item.get('protocol'),
                          'type': item.get('type'), 'method': item.get('method'),
                          'is-allowed': item.get('isAllowed'),
                          'clickjacking-protection': item.get('clickjackingProtection'),
                          'perform-staging': item.get('performStaging'),
                          'mandatory-body': item.get('mandatoryBody'),
                          'self-link': item.get('selfLink'),
                          'last-update': format_date(item.get('lastUpdateMicros'))}
        printable_result.append(current_object)
    outputs = {'f5.Url(val.uid && val.uid == obj.uid)': printable_result}
    readable_output = tableToMarkdown("URL for selected policy", printable_result,
                                      headers=['id', 'name', 'description', 'protocol', 'type',
                                               'method', 'is-allowed',
                                               'clickjacking-protection', 'perform-staging',
                                               'mandatory-body', 'self-link',
                                               'last-update'], removeNull=True)
    return readable_output, outputs, result


def format_policy_url_command(result: dict):
    """
        Formats a single resource URL for demisto
        Args:
            result(dict): API response from F5.

        Returns:
                str: the markdown to display inside Demisto.
                dict: the context to return into Demisto.
                dict: the report from f5 (used for debugging).
    """
    current_object = {'id': result.get('id'),
                      'name': result.get('name'),
                      'description': result.get('description'),
                      'protocol': result.get('protocol'),
                      'type': result.get('type'),
                      'method': result.get('method'),
                      'is-allowed': result.get('isAllowed'),
                      'clickjacking-protection': result.get('clickjackingProtection'),
                      'perform-staging': result.get('performStaging'),
                      'mandatory-body': result.get('mandatoryBody'),
                      'self-link': result.get('selfLink'),
                      'last-update': format_date(result.get('lastUpdateMicros'))}
    printable_result = current_object
    outputs = {'f5.Url(val.uid && val.uid == obj.uid)': printable_result}
    readable_output = tableToMarkdown("URL for selected policy", printable_result,
                                      headers=['id', 'name', 'description', 'protocol', 'type',
                                               'method', 'is-allowed',
                                               'clickjacking-protection', 'perform-staging',
                                               'mandatory-body', 'self-link',
                                               'last-update'], removeNull=True)
    return readable_output, outputs, result


def format_list_cookies(result: dict):
    """
        Formats f5 policy cookies to Demisto's outputs.

    Args:
        result (dict): the report from f5.

    Returns:
        str: the markdown to display inside Demisto.
        dict: the context to return into Demisto.
        dict: the report from f5 (used for debugging).
    """
    if not result:
        return 'No data to show.', {}, result

    result = result.get('items')
    if not result:
        return 'No data to show.', {}, result

    printable_result = []
    for item in result:
        current_object_data = {
            'name': item.get('name'),
            'id': item.get('id'),
            'self-link': item.get('selfLink'),
            'enforcement-type': item.get('enforcementType'),
            'perform-staging': item.get('performStaging'),
            'kind': item.get('kind'),
            'is-base-64': item.get('isBase64'),
            'created-by': item.get('createdBy'),
        }
        printable_result.append(current_object_data)
    outputs = {'f5.Cookies(val.uid && val.uid == obj.uid)': printable_result}
    readable_output = tableToMarkdown('f5 data for policy cookies:', printable_result,
                                      ['name', 'id', 'self-link', 'enforcement-type',
                                       'perform-staging', 'kind', 'is-base-64', 'created-by'],
                                      removeNull=True)

    return readable_output, outputs, result


def format_cookies_command(result: dict, action: str):
    """
        Formats f5 policy cookie to Demisto's outputs.

    Args:
        result (dict): the report from f5.
        action (str): The action taken on a policy cookie.

    Returns:
        str: the markdown to display inside Demisto.
        dict: the context to return into Demisto.
        dict: the report from f5 (used for debugging).
    """
    if not result:
        return 'No data to show.', {}, result

    printable_result = {
        'name': result.get('name'),
        'id': result.get('id'),
        'self-link': result.get('selfLink'),
        'enforcement-type': result.get('enforcementType'),
        'perform-staging': result.get('performStaging'),
        'type': result.get('type'),
        'is-base-64': result.get('isBase64'),
        'created-by': result.get('createdBy'),
    }
    outputs = {'f5.Cookies(val.uid && val.uid == obj.uid)': printable_result}
    readable_output = tableToMarkdown(f'f5 data for {action} policy cookies:', printable_result,
                                      ['name', 'id', 'self-link', 'enforcement-type',
                                       'perform-staging', 'type', 'is-base-64', 'created-by'],
                                      removeNull=True)
    return readable_output, outputs, result


def format_policy_whitelist_ips_command(result: dict):
    """
        Formats multiple whitelisted IPs for Demisto to show.

        Args:
            result (dict): the report from f5.

        Returns:
            str: the markdown to display inside Demisto.
            dict: the context to return into Demisto.
            dict: the report from f5 (used for debugging).
    """

    if not result:
        return 'No data to show.', {}, result

    result = result.get('items')
    if not result:
        return 'No data to show.', {}, result

    printable_result = []
    for item in result:
        current_object_data = {
            'id': item.get('id'),
            'self-link': item.get('selfLink'),
            'ip-address': item.get('ipAddress'),
            'ip-mask': item.get('ipMask'),
            'description': item.get('description'),
            'block-requests': item.get('blockRequests'),
            'ignore-anomalies': item.get('ignoreAnomalies'),
            'never-log-requests': item.get('neverLogRequests'),
            'never-learn-requests': item.get('neverLearnRequests'),
            'trusted-by-policy-builder': item.get('trustedByPolicyBuilder'),
            'last-update': format_date(item.get('lastUpdateMicros')),
        }
        printable_result.append(current_object_data)
    outputs = {'f5.WhitelistIP(val.uid && val.uid == obj.uid)': printable_result}
    readable_output = tableToMarkdown('f5 data for resource whitelisted IPs:', printable_result,
                                      ['id', 'ip-address', 'ip-mask', 'description',
                                       'block-requests', 'ignore-anomalies',
                                       'never-log-requests', 'never-learn-requests',
                                       'trusted-by-policy-builder', 'self-link', 'last-update'],
                                      removeNull=True)

    return readable_output, outputs, result


def format_policy_whitelist_ip_command(result: dict, action: str):
    """
        Format a single whitelisted IP to demisto.

        Args:
            result (dict): the report from f5.
            action (str): Created / Updated / Deleted.

        Returns:
            str: the markdown to display inside Demisto.
            dict: the context to return into Demisto.
            dict: the report from f5 (used for debugging).
    """
    if not result:
        return 'No data to show.', {}, result

    printable_result = {
        'id': result.get('id'),
        'self-link': result.get('selfLink'),
        'ip-address': result.get('ipAddress'),
        'ip-mask': result.get('ipMask'),
        'description': result.get('description'),
        'block-requests': result.get('blockRequests'),
        'ignore-anomalies': result.get('ignoreAnomalies'),
        'never-log-requests': result.get('neverLogRequests'),
        'never-learn-requests': result.get('neverLearnRequests'),
        'trusted-by-policy-builder': result.get('trustedByPolicyBuilder'),
        'last-update': format_date(result.get('lastUpdateMicros')),
    }
    outputs = {'f5.WhitelistIP(val.uid && val.uid == obj.uid)': printable_result}
    readable_output = tableToMarkdown(f'f5 data for {action} resource whitelisted IP:',
                                      printable_result,
                                      ['id', 'ip-address', 'ip-mask',
                                       'description', 'block-requests', 'ignore-anomalies',
                                       'never-log-requests', 'never-learn-requests',
                                       'trusted-by-policy-builder', 'self-link', 'last-update'],
                                      removeNull=True)
    return readable_output, outputs, result


def format_date(date):
    """formats date according to Demisto date format"""
    date = int(date / 1000000)
    return time.strftime(DATE_FORMAT, time.localtime(date))


def main():
    """
        PARSE AND VALIDATE INTEGRATION PARAMS
    """
    params = demisto.params()
    username = params.get('credentials', {}).get('identifier')
    password = params.get('credentials', {}).get('password')

    server_ip = params['url']
    base_url = f'https://{server_ip}/mgmt/tm/'

    verify_certificate = not params.get('insecure', False)
    proxy = params.get('proxy', False)

    token = login(server_ip, username, password, verify_certificate)

    LOG(f'Command being called is {demisto.command()}')
    try:

        if demisto.command() == 'test-module':
            result = test_module(base_url, username, password, verify_certificate)
            demisto.results(result)

        client = Client(
            base_url=base_url,
            token=token,
            use_ssl=verify_certificate,
            use_proxy=proxy)
        command = demisto.command()
        commands = {
            'f5-asm-policy-list': client.f5_list_policies_command,
            'f5-asm-policy-apply': client.f5_apply_policy_command,
            'f5-asm-policy-export-file': client.f5_export_policy_command,
            'f5-asm-policy-delete': client.f5_delete_policy_command,

            'f5-asm-policy-methods-list': client.f5_list_policy_methods_command,
            'f5-asm-policy-methods-add': client.f5_add_policy_methods_command,
            'f5-asm-policy-methods-update': client.f5_update_policy_methods_command,
            'f5-asm-policy-methods-delete': client.f5_delete_policy_methods_command,

            'f5-asm-policy-file-type-list': client.f5_list_policy_file_types_command,
            'f5-asm-policy-file-type-add': client.f5_add_policy_file_types_command,
            'f5-asm-policy-file-type-update': client.f5_update_policy_file_types_command,
            'f5-asm-policy-file-type-delete': client.f5_delete_policy_file_types_command,

            'f5-asm-policy-cookies-list': client.f5_list_policy_cookies_command,
            'f5-asm-policy-cookies-add': client.f5_add_policy_cookies_command,
            'f5-asm-policy-cookies-update': client.f5_update_policy_cookies_command,
            'f5-asm-policy-cookies-delete': client.f5_delete_policy_cookies_command,

            'f5-asm-policy-hostnames-list': client.f5_list_policy_hostname_command,
            'f5-asm-policy-hostnames-add': client.f5_add_policy_hostname_command,
            'f5-asm-policy-hostnames-update': client.f5_update_policy_hostname_command,
            'f5-asm-policy-hostnames-delete': client.f5_delete_policy_hostname_command,

            'f5-asm-policy-blocking-settings-list':
                client.f5_list_policy_blocking_settings_command,
            'f5-asm-policy-blocking-settings-update':
                client.f5_update_policy_blocking_settings_command,

            'f5-asm-policy-urls-list': client.f5_list_policy_urls_command,
            'f5-asm-policy-urls-add': client.f5_add_policy_url_command,
            'f5-asm-policy-urls-update': client.f5_update_policy_url_command,
            'f5-asm-policy-urls-delete': client.f5_delete_policy_url_command,

            'f5-asm-policy-whitelist-ips-list': client.f5_list_policy_whitelist_ips_command,
            'f5-asm-policy-whitelist-ips-add': client.f5_add_policy_whitelist_ips_command,
            'f5-asm-policy-whitelist-ips-update': client.f5_update_policy_whitelist_ips_command,
            'f5-asm-policy-whitelist-ips-delete': client.f5_delete_policy_whitelist_ips_command,
        }

        if command in commands:
            readable_output, outputs, result = (commands[demisto.command()](**demisto.args()))
            return_outputs(readable_output, outputs, result)

    except Exception as e:
        return_error(f'Failed to execute {demisto.command()} command. Error: {str(e)}')


if __name__ in ('__main__', '__builtin__', 'builtins'):
    main()
