#!/usr/bin/python
#coding: utf-8 -*-

from time import sleep
try:
    import shade
    HAS_SHADE = True
except ImportError:
    HAS_SHADE = False

DOCUMENTATION = '''
---
module: os_stack
short_description: Add/Remove Heat Stack
extends_documentation_fragment: openstack
version_added: "2.0"
author: "Mathieu Bultel (matbu)"
description:
   - Add or Remove a Stack to an OpenStack Heat
options:
    state:
      description:
        - Indicate desired state of the resource
      choices: ['present', 'absent']
      required: false
      default: present
    name:
      description:
        - Name of the stack that should be created
      required: true
      default: None
    template:
      description:
        - Path of the template file to use for the stack creation
      required: false
      default: None
    environment:
      description:
        - List of environment files that should be used for the stack creation
      required: false
      default: None
    parameters:
      description:
        - Dictionary of parameters for the stack creation
      required: false
    rollback:
      description:
        - Rollback stack creation
      required: false
      default: false
    timeout:
      description:
        - Maximum number of seconds to wait for the stack creation
      required: false
      default: 3600
requirements:
    - "python >= 2.6"
    - "shade"
'''
EXAMPLES = '''
---
- name: create stack
  ignore_errors: True
  register: stack_create
  os_heat:
    name: "{{ stack_name }}"
    state: present
    template: "/path/to/my_stack.yaml"
    environment:
    - /path/to/resource-registry.yaml
    - /path/to/environment.yaml
    parameters:
        os_user: {{ os_user }}
        os_password: {{ os_password }}
        os_tenant: {{ os_tenant }}
        os_auth_url: {{ os_auth_url }}
        bmc_flavor: m1.medium
        bmc_image: CentOS
        key_name: default
        private_net: {{ private_net_param }}
        node_count: 2
        name: undercloud
        image: CentOS
        my_flavor: m1.large
        external_net: {{ external_net_param }}
'''

def _create_stack(module, stack, cloud):
    try:
        stack = cloud.create_stack(module.params['name'],
                                       template_file=module.params['template'],
                                       environment_files=module.params['environment'],
                                       timeout=module.params['timeout'],
                                       wait=True,
                                       rollback=module.params['rollback'],
                                       **module.params['parameters'])

        stack = cloud.get_stack(stack.id, None)
        if stack.stack_status == 'CREATE_COMPLETE':
            return stack
        else:
            return False
            module.fail_json(msg = "Failure in creating stack: ".format(stack))
    except shade.OpenStackCloudException as e:
        module.fail_json(msg=e.message)

def _system_state_change(module, stack, cloud):
    state = module.params['state']
    if state == 'present':
        if not stack:
            return True
    if state == 'absent' and stack:
        return True
    return False

def main():

    argument_spec = openstack_full_argument_spec(
        name=dict(required=True),
        template=dict(default=None),
        environment=dict(default=None, type='list'),
        parameters=dict(default={}, type='dict'),
        rollback=dict(default=False),
        timeout=dict(default=3600, type='int'),
        state=dict(default='present', choices=['absent', 'present']),
    )

    module_kwargs = openstack_module_kwargs()
    module = AnsibleModule(argument_spec,
                           supports_check_mode=True,
                           **module_kwargs)

    if not HAS_SHADE:
        module.fail_json(msg='shade is required for this module')

    state = module.params['state']
    name = module.params['name']
    # Check for required parameters when state == 'present'
    if state == 'present':
        for p in ['template']:
            if not module.params[p]:
                module.fail_json(msg='%s required with present state' % p)

    try:
        cloud = shade.openstack_cloud(**module.params)
        stack = cloud.get_stack(name)

        if state == 'present':
            if not stack:
                stack = _create_stack(module, stack, cloud)
                changed = True
            else:
                changed = False
            module.exit_json(changed=changed,
                             stack=stack,
                             id=stack.id)
        elif state == 'absent':
            if not stack:
                changed = False
            else:
                changed = True
                if not cloud.delete_stack(name, wait=True):
                    module.fail_json(msg='delete stack failed for stack: %s' % name)
            module.exit_json(changed=changed)
    except shade.OpenStackCloudException as e:
        module.fail_json(msg=e.message)

from ansible.module_utils.basic import *
from ansible.module_utils.openstack import *
if __name__ == '__main__':
    main()
