import subprocess as sp
from subprocess import call

import charms.leadership
from charmhelpers.core import unitdata
from charmhelpers.core.hookenv import (application_version_set, config,
                                       network_get, open_port, relation_set,
                                       status_set, unit_get, leader_get)
from charmhelpers.core.services.base import service_restart
# from charmhelpers.core.templating import render
from charmhelpers.fetch import get_upstream_version
from charms.reactive import clear_flag, set_flag, when, when_any, when_not, endpoint_from_flag

PRIVATE_IP = network_get('http')['ingress-addresses'][0]
MAAS_WEB_PORT = 5240


set_flag('maas.mode.{}'.format(config('maas-mode')))
# status_set('maintenance', 'MAAS {} Configuration'.format(config('maas-mode')))

kv = unitdata.kv()

def maas_url():
    if config('maas-url'):
        return config('maas-url')
    else:
        return 'http://{}:5240/MAAS'.format(PRIVATE_IP)

@when('maas.mode.region')
@when_not('apt.installed.maas-region-api')
def install_maas_region_api():
    charms.apt.queue_install(['maas-region-api'])

@when('maas.mode.region',
      'apt.installed.maas-region-api')
@when_not('maas.version.set')
def set_message_version():
    application_version_set(get_upstream_version('maas-region-api'))

    # message = sp.check_output('maas', '--version', stderr=sp.STDOUT)
    
    status_set('maintenance', 'Region installed, waiting for DB rel' )

    set_flag('maas.version.set')
# @when_not('postgresql.connected')
# def set_waiting_for_db_relation():
#     status_set('waiting', 'Waiting for PGSQL Relation')

@when('maas.mode.region',
      'postgresql.connected')
@when_not('maas.database.requested')
def request_postgresql_database_for_maas_region(pgsql):
    """Request PGSql DB
    """

    conf = config()
    status_set('maintenance', 'Requesting MAASDB')

    pgsql.set_database(conf.get('db-name', 'maasdb'))
    if conf.get('db-roles'):
        pgsql.set_roles(conf.get('db-roles'))
    if conf.get('db-extensions'):
        pgsql.set_extensions(conf.get('db-extensions'))
    status_set('active', 'MAASDB requested')
    set_flag('maas.database.requested')

@when('maas.mode.region',
      'postgresql.master.available',
      'maas.database.requested')
@when_not('maas.juju.database.available')
def get_set_postgresql_data_for_maas_db(pgsql):
    """Get/set postgresql details
    """

    status_set('maintenance', 'Database acquired, saving details')
    kv.set('db_host', pgsql.master.host)
    kv.set('db_name', pgsql.master.dbname)
    kv.set('db_pass', pgsql.master.password)
    kv.set('db_user', pgsql.master.user)
    status_set('active', 'MAASDB saved to unitdata')

    clear_flag('maas.manual.database.available')
    set_flag('maas.juju.database.available')

@when('maas.mode.region',
      'apt.installed.maas-region-api',
      'leadership.is_leader',
      'maas.juju.database.available')
@when_not('maas.init.complete')
def maas_leader_init():
    """Init MAAS (region, region+rack) - only leader should run this code
    """
    status_set('maintenance',
               'Configuring MAAS-{}'.format(config('maas-mode')))

    init_ctxt = {'maas_url': maas_url(),
                 'maas_mode': config('maas-mode'),
                 'db_host': kv.get('db_host'),
                 'db_name': kv.get('db_name'),
                 'db_pass': kv.get('db_pass'),
                 'db_user': kv.get('db_user')}

    cmd_init = ('maas-region local_config_set --maas-url {maas_url} --database-host {db_host} '
                '--database-name {db_name} --database-user {db_user} '
                '--database-pass {db_pass}'.format(**init_ctxt))

    createadmin_ctxt = {'maas_username': config('admin-username'),
                        'maas_password': config('admin-password'),
                        'maas_email': config('admin-email'),
                        'maas_ssh_import': config('admin-ssh-import')}

    cmd_dbupgrade = ('maas-region dbupgrade'.format())

    cmd_createadmin = ('maas createadmin --username {maas_username} --password {maas_password} '
                       '--email {maas_email} --ssh-import {maas_ssh_import}'.format(**createadmin_ctxt))

    call(cmd_init.split())
    call(cmd_dbupgrade.split())
    service_restart('maas-regiond')
    call(cmd_createadmin.split())

    status_set('active', 'MAAS-{} configured'.format(config('maas-mode')))
    set_flag('maas.init.complete')

@when('maas.mode.region',
      'maas.init.complete',
      'leadership.is_leader')
@when_not('maas.secret.published')
def get_set_secret():
    status_set('maintenance', 'Retrieving Rack Secret')
    with open("/var/lib/maas/secret", 'r') as f:
        charms.leadership.leader_set(secret=f.read())
    set_flag('maas.secret.published')

@when('maas.init.complete')
@when_any('maas.mode.region',
          'maas.mode.all',
          'maas.mode.region+rack')
@when_not('maas.http.available')
def open_web_port():
    open_port(MAAS_WEB_PORT)
    status_set('active', 'MAAS http available')
    set_flag('maas.http.available')


@when('leadership.set.secret',
      'leadership.is_leader',
      'endpoint.region.available')
@when('maas.mode.region')
@when_not('region.relation.data.available')
def send_relation_data_to_rack():
    endpoint = endpoint_from_flag('endpoint.region.available')
    ctxt = {'secret': leader_get('secret'),
            'maas_url': maas_url()}
    endpoint.configure(**ctxt)
    set_flag('region.relation.data.available')

# @when('maas.mode.region')
# @when('maas.secret.published')
# def set_leader_ready():
#     status_set('active', "Region Controller Ready")

### RACK CONTROLLER LOGIC

@when('maas.mode.rack')
@when_not('apt.installed.maas-rack-controller')
def install_maas_rack_controller():
    charms.apt.queue_install(['maas-rack-controller'])

@when('maas.mode.rack',
      'apt.installed.maas-rack-controller')
@when_not('maas.version.set')
def set_message_version():
    application_version_set(get_upstream_version('maas-rack-controller'))
    
    status_set('maintenance', 'Rack Installed, waiting for Region rel' )

    set_flag('maas.version.set')

# @when('maas.mode.rack')
# @when('apt.installed.maas-rack-controller')
# @when_not('endpoint.rack.available')
# def set_rack_waiting_relation():
#     status_set('waiting', 'Waiting for Region Relation' )


@when('maas.mode.rack',
      'endpoint.rack.available',
      'apt.installed.maas-rack-controller')
@when_not('rack.relation.data.available')
def acquire_config_from_region_controller():
    """Acquire maas_url and secret from region
    """
    status_set('maintenance',
               'Acquiring configuration details from region controller')
    endpoint = endpoint_from_flag('endpoint.rack.available')
    for unit in endpoint.list_unit_data():
        kv.set('maas_url', unit['maas_url'])
        kv.set('secret', unit['secret'])
    status_set('active', 'Region configuration acquired')
    set_flag('rack.relation.data.available')

@when('maas.mode.rack',
      'rack.relation.data.available')
@when_not('maas.rack.init.complete')
def configure_maas_rack():
    """Configure rack controller now that we have what we need
    """
    status_set('maintenance', 'Rack initializing')
    init_ctxt = {'maas_url': kv.get('maas_url'),
                 'secret': kv.get('secret')}
    cmd_init = \
        ('maas-rack register --url {maas_url} --secret {secret} '.format(**init_ctxt))
    call(cmd_init.split())
    status_set('active', 'Rack init complete')
    set_flag('maas.init.complete')
    set_flag('maas.rack.init.complete')



@when('maas.init.complete',
      'maas.mode.rack')
@when_not('rack_region_connected')
def set_connected_status():
    status_set('active', "Region <-> Rack connected")
    set_flag('rack_region_connected')
