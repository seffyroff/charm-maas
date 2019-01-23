from charms.reactive import when, when_not, when_any, set_flag, clear_flag
from charmhelpers.core.hookenv import application_version_set, status_set, network_get, config, open_port
from charmhelpers.core import unitdata
from charmhelpers.core.services.base import service_restart
from charmhelpers.fetch import get_upstream_version
import subprocess as sp
from subprocess import call
from charmhelpers.core.templating import render

PRIVATE_IP = network_get('http')['ingress-addresses'][0]
MAAS_WEB_PORT = 5240


set_flag('maas.mode.{}'.format(config('maas-mode')))

kv = unitdata.kv()

def maas_url():
    if config('maas-url'):
        return config('maas-url')
    else:
        return 'http://{}:5240/MAAS'.format(PRIVATE_IP)


@when_not('maas-region-ppa.installed')
def install_maas_region_ppa():
    set_flag('maas-region-ppa.installed')

@when('apt.installed.maas-region-controller')
def set_message_version():
    application_version_set(get_upstream_version('maas-region-controller'))

    # message = sp.check_output('maas', '--version', stderr=sp.STDOUT)
    
    # status_set('maintenance', message )

    set_flag('maas.version.set')
# @when_not('postgresql.connected')
# def set_waiting_for_db_relation():
#     status_set('waiting', 'Waiting for PGSQL Relation')

@when('postgresql.connected')
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

@when('postgresql.master.available',
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

@when('maas-region-ppa.installed')
@when('maas.juju.database.available')
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

