# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2011 OpenStack LLC.
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import sqlite3
import MySQLdb as mdb
import threading 


from balancer.loadbalancers.loadbalancer import *
from openstack.common import exception
from balancer.devices.device import LBDevice
from balancer.core.configuration import Configuration
from balancer.loadbalancers.probe import *
from balancer.loadbalancers.sticky import *
from balancer.loadbalancers.realserver import RealServer
from balancer.loadbalancers.predictor import *
from balancer.loadbalancers.serverfarm import ServerFarm
from balancer.loadbalancers.virtualserver import VirtualServer
from balancer.loadbalancers.vlan import VLAN
logger = logging.getLogger(__name__)


DATABASE_TYPE = 'mysql'
class SQLExecute(object):
    def execute(self,cursor,  command):
        executed = False
        while (not executed):
            try:
                cursor.execute(command)
                executed = True
            except OperationalError as ex:
                logger.info("Got database exception. Msg: %s" % ex.message)
                
                

class Reader(SQLExecute):
    """ Reader class is used for db read opreations"""
    def __init__(self,  db):
        logger.debug("Reader: connecting to db: %s" % db)
        if DATABASE_TYPE =='mysql':
            self._con = mdb.connect('localhost',  'root',  'swordfish',  'balancer')
        else:
            self._con = sqlite3.connect(db)
        self._probeDict = {'DNS': DNSprobe(), 'ECHO TCP': ECHOTCPprobe(), \
                        'ECHO-UDP': ECHOUDPprobe(), 'FINGER': FINGERprobe(), \
                        'FTP': FTPprobe(), 'HTTPS': HTTPSprobe(), \
                        'HTTP': HTTPprobe(), 'ICMP': ICMPprobe(), \
                        'IMAP': IMAPprobe(), 'POP': POPprobe(), \
                        'RADIUS': RADIUSprobe(), 'RTSP': RTSPprobe(), \
                        'SCRIPTED': SCRIPTEDprobe(), 'SIP TCP': SIPTCPprobe(), \
                        'SIP UDP': SIPUDPprobe(), 'SMTP': SMTPprobe(), \
                        'SNMP': SNMPprobe(), 'CONNECT': TCPprobe(), \
                        'TELNET': TELNETprobe(), 'UDP': UDPprobe(), \
                        'VM': VMprobe()}
        self._predictDict = {'HashAddrPredictor': HashAddrPredictor(), \
                          'HashContent': HashContent(), \
                          'HashCookie': HashCookie(), \
                          'HashHeader': HashHeader(),
                          'HashLayer4': HashLayer4(), 'HashURL': HashURL(), \
                          'LeastBandwidth': LeastBandwidth(), \
                          'LeastConnections': LeastConn(), \
                          'LeastLoaded': LeastLoaded(), \
                          'Response': Response(), 'RoundRobin': RoundRobin()}
                          
        self._stickyDict = {'http-content': HTTPContentSticky(), \
                                    'http-cookie': HTTPCookieSticky(), \
                                    'http-header': HTTPHeaderSticky(), \
                                    'ip-netmask': IPNetmaskSticky(), \
                                    'layer4-payload': L4PayloadSticky(), \
                                    'rtsp-header': RTSPHeaderSticky(), \
                                    'radius': RadiusSticky(), \
                                    'sip-header': SIPHeaderSticky(), \
                                    'v6prefix': v6PrefixSticky()}

    def getLoadBalancers(self,  tenant_id):
        self._con.row_factory = sqlite3.Row
        if DATABASE_TYPE == 'mysql':
            cursor = self._con.cursor(mdb.cursors.DictCursor)
        else:
            cursor = self._con.cursor()
        cursor.execute('SELECT * FROM loadbalancers WHERE tenant_id="%s"' % tenant_id)
        rows = cursor.fetchall()
        if rows == None:
            raise exception.NotFound()
        list = []
        for row in rows:
            lb = LoadBalancer()
            lb.loadFromDict(row)
            list.append(lb)
        return list

    def getLoadBalancerById(self,  id):
        self._con.row_factory = sqlite3.Row
        if DATABASE_TYPE == 'mysql':
            cursor = self._con.cursor(mdb.cursors.DictCursor)
        else:
            cursor = self._con.cursor()
        cursor.execute('SELECT * FROM loadbalancers WHERE id = "%s"' % id)
        row = cursor.fetchone()
        if row == None:
            raise exception.NotFound()
        lb = LoadBalancer()
        lb.loadFromDict(row)
        return lb

    def getDeviceById(self,  id):
        self._con.row_factory = sqlite3.Row
        if DATABASE_TYPE == 'mysql':
            cursor = self._con.cursor(mdb.cursors.DictCursor)
        else:
            cursor = self._con.cursor()
        if id == None:
            raise exception.NotFound("Empty device id.")
        cursor.execute('SELECT * FROM devices WHERE id = "%s"' % id)
        row = cursor.fetchone()
        if row == None:
            raise exception.NotFound()
        lb = LBDevice()
        lb.loadFromDict(row)
        return lb

    def getDeviceByLBid(self,  id):
        self._con.row_factory = sqlite3.Row
        if DATABASE_TYPE == 'mysql':
            cursor = self._con.cursor(mdb.cursors.DictCursor)
        else:
            cursor = self._con.cursor()
        if id == None:
            raise exception.NotFound("Empty device id.")
        cursor.execute('SELECT * FROM loadbalancers WHERE id = "%s"' % id)
        row = cursor.fetchone()
        cursor.execute('SELECT * FROM devices WHERE id = "%s"' % \
                                                  row['device_id'])
        dict = cursor.fetchone()
        if dict == None:
            raise exception.NotFound()
        lb = LBDevice()
        lb.loadFromDict(dict)

    def getDevices(self):
        self._con.row_factory = sqlite3.Row
        if DATABASE_TYPE == 'mysql':
            cursor = self._con.cursor(mdb.cursors.DictCursor)
        else:
            cursor = self._con.cursor()
        cursor.execute('SELECT * FROM devices')
        rows = cursor.fetchall()
        if rows == None:
            raise exception.NotFound()
        list = []
        for row in rows:
            lb = LBDevice()
            lb.loadFromDict(row)
            list.append(lb)
        return list

    def getProbeById(self, id):
        self._con.row_factory = sqlite3.Row
        if DATABASE_TYPE == 'mysql':
            cursor = self._con.cursor(mdb.cursors.DictCursor)
        else:
            cursor = self._con.cursor()
        cursor.execute('SELECT * FROM probes WHERE id = "%s"' % id)
        row = cursor.fetchone()
        if row == None:
            raise exception.NotFound()
        prb = self._probeDict[row['type']].createSame()
        prb.loadFromDict(row)
        return prb

    def getProbes(self):
        self._con.row_factory = sqlite3.Row
        if DATABASE_TYPE == 'mysql':
            cursor = self._con.cursor(mdb.cursors.DictCursor)
        else:
            cursor = self._con.cursor()
        cursor.execute('SELECT * FROM probes')
        rows = cursor.fetchall()
        if rows == None:
            raise exception.NotFound()
        list = []
        for row in rows:
            prb = self._probeDict[row['type']].createSame()
            prb.loadFromDict(row)
            list.append(prb)
        return list

    def getStickyById(self, id):
        self._con.row_factory = sqlite3.Row
        if DATABASE_TYPE == 'mysql':
            cursor = self._con.cursor(mdb.cursors.DictCursor)
        else:
             cursor = self._con.cursor()
        cursor.execute('SELECT * FROM stickies WHERE id = "%s"' % id)
        row = cursor.fetchone()
        if row == None:
            raise exception.NotFound()
        st = self._stickyDict[row['type']].createSame()
        st.loadFromDict(row)
        return st

    def getStickies(self):
        self._con.row_factory = sqlite3.Row
        if DATABASE_TYPE == 'mysql':
            cursor = self._con.cursor(mdb.cursors.DictCursor)
        else:
            cursor = self._con.cursor()
        cursor.execute('SELECT * FROM stickies')
        rows = cursor.fetchall()
        if rows == None:
            raise exception.NotFound()
        list = []
        for row in rows:
            st = self._stickyDict[row['type']].createSame()
            st.loadFromDict(row)
            list.append(st)
        return list
        
    def getRServerById(self,  id):
        self._con.row_factory = sqlite3.Row
        if DATABASE_TYPE == 'mysql':
            cursor = self._con.cursor(mdb.cursors.DictCursor)
        else:
            cursor = self._con.cursor()
        if id == None:
            raise exception.NotFound("Empty device id.")
        cursor.execute('SELECT * FROM rservers WHERE id = "%s"' % id)
        row = cursor.fetchone()
        if row == None:
            raise exception.NotFound()
        rs = RealServer()
        rs.loadFromDict(row)
        return rs

    def getRServerByIP(self,  ip):
        self._con.row_factory = sqlite3.Row
        if DATABASE_TYPE == 'mysql':
            cursor = self._con.cursor(mdb.cursors.DictCursor)
        else:
            cursor = self._con.cursor()
        if ip == None:
            raise exception.NotFound("Empty device ip.")
        cursor.execute('SELECT * FROM rservers WHERE address= "%s" and deployed="True"' % ip)
        row = cursor.fetchone()
        if row == None:
            raise exception.NotFound()
        rs = RealServer()
        rs.loadFromDict(row)
        return rs

    def getRServersByParentID(self,  id):
        self._con.row_factory = sqlite3.Row
        if DATABASE_TYPE == 'mysql':
            cursor = self._con.cursor(mdb.cursors.DictCursor)
        else:
            cursor = self._con.cursor()
        if id == None:
            raise exception.NotFound("Empty rservers ip.")
        cursor.execute('SELECT * FROM rservers WHERE parent_id= "%s"' % id)
        rows = cursor.fetchall()
        if rows == None:
            raise exception.NotFound()
        list = []
        for row in rows:
            rs = RealServer()
            rs.loadFromDict(row)
            list.append(rs)
        return list

    def getRServers(self):
        self._con.row_factory = sqlite3.Row
        if DATABASE_TYPE == 'mysql':
            cursor = self._con.cursor(mdb.cursors.DictCursor)
        else:
            cursor = self._con.cursor()
        cursor.execute('SELECT * FROM rservers')
        rows = cursor.fetchall()
        if rows == None:
            raise exception.NotFound()
        list = []
        for row in rows:
            rs = RealServer()
            rs.loadFromDict(row)
            list.append(rs)
        return list
        
    def getLoadBalancersByVMid(self,  vm_id,  tenant_id):
        self._con.row_factory = sqlite3.Row
        if DATABASE_TYPE == 'mysql':
            cursor = self._con.cursor(mdb.cursors.DictCursor)
        else:
            cursor = self._con.cursor()
        command = 'SELECT rservers.id, serverfarms.lb_id FROM rservers, \
        serverfarms, loadbalancers WHERE rservers.vm_id="%s" AND rservers.sf_id=serverfarms.id AND \
        loadbalancers.id = serverfarms.lb_id and loadbalancers.tenant_id="%s"' % (vm_id,  tenant_id)
        logger.debug("Executing command to retrieve loadbalancer for vm: %s" % command)
        cursor.execute(command)
        rows = cursor.fetchall()
        if rows == None:
            raise exception.NotFound()
        list = []
        for row in rows:
            lb_id = row['lb_id']
            lb = self.getLoadBalancerById(lb_id)
            list.append(lb)
        return list

    def getRServersByVMid(selfself,  vm_id):
        self._con.row_factory = sqlite3.Row
        if DATABASE_TYPE == 'mysql':
            cursor = self._con.cursor(mdb.cursors.DictCursor)
        else:
            cursor = self._con.cursor()
        cursor.execute('SELECT * FROM rservers WHERE rservers.vm_id="%s"' % vm_id)
        rows = cursor.fetchall()
        if rows == None:
            raise exception.NotFound()
        list = []
        for row in rows:
            rs = RealServer()
            rs.loadFromDict(row)
            list.append(rs)
        return list

    def getRServersByVMidForLB(selfself,  vm_id,  lb_id):
        self._con.row_factory = sqlite3.Row
        if DATABASE_TYPE == 'mysql':
            cursor = self._con.cursor(mdb.cursors.DictCursor)
        else:
            cursor = self._con.cursor()
        cursor.execute('SELECT rservers.* FROM rservers, serverfarms WHERE \
        rservers.vm_id="%s" and rservers.sf_id=serverfarms.id and serverframs.lb_id="%s" ' % (vm_id,  lb_id))
        rows = cursor.fetchall()
        if rows == None:
            raise exception.NotFound()
        list = []
        for row in rows:
            rs = RealServer()
            rs.loadFromDict(row)
            list.append(rs)
        return list
        
    def getPreditorById(self, id):
        self._con.row_factory = sqlite3.Row
        if DATABASE_TYPE == 'mysql':
            cursor = self._con.cursor(mdb.cursors.DictCursor)
        else:
            cursor = self._con.cursor()
        cursor.execute('SELECT * FROM predictors WHERE id = "%s"' % id)
        row = cursor.fetchone()
        if row == None:
            raise exception.NotFound()
        prd = self._predictDict[row['type']].createSame()
        prd.loadFromDict(row)
        return prd

    def getPredictors(self):
        self._con.row_factory = sqlite3.Row
        if DATABASE_TYPE == 'mysql':
            cursor = self._con.cursor(mdb.cursors.DictCursor)
        else:
            cursor = self._con.cursor()
        cursor.execute('SELECT * FROM predictors')
        rows = cursor.fetchall()
        if rows == None:
            raise exception.NotFound()
        list = []
        for row in rows:
            prd = self._predictDict[row['type']].createSame()
            prd.loadFromDict(row)
            list.append(prd)
        return list

    def getServerFarmById(self, id):
        self._con.row_factory = sqlite3.Row
        if DATABASE_TYPE == 'mysql':
            cursor = self._con.cursor(mdb.cursors.DictCursor)
        else:
            cursor = self._con.cursor()
        cursor.execute('SELECT * FROM serverfarms WHERE id = "%s"' % id)
        row = cursor.fetchone()
        if row == None:
            raise exception.NotFound()
        sf = ServerFarm()
        sf.loadFromDict(row)
        return sf

    def getServerFarms(self):
        self._con.row_factory = sqlite3.Row
        if DATABASE_TYPE == 'mysql':
            cursor = self._con.cursor(mdb.cursors.DictCursor)
        else:
            cursor = self._con.cursor()
        cursor.execute('SELECT * FROM serverfarms')
        rows = cursor.fetchall()
        if rows == None:
            raise exception.NotFound()
        list = []
        for row in rows:
            sf = ServerFarm()
            sf.loadFromDict(row)
            list.append(sf)
        return list

    def getVirtualServerById(self, id):
        self._con.row_factory = sqlite3.Row
        if DATABASE_TYPE == 'mysql':
            cursor = self._con.cursor(mdb.cursors.DictCursor)
        else:
            cursor = self._con.cursor()
        cursor.execute('SELECT * FROM vips WHERE id = "%s"' % id)
        row = cursor.fetchone()
        if row == None:
            raise exception.NotFound()
        vs = VirtualServer()
        vs.loadFromDict(row)
        return vs

    def getVirtualServers(self):
        self._con.row_factory = sqlite3.Row
        if DATABASE_TYPE == 'mysql':
            cursor = self._con.cursor(mdb.cursors.DictCursor)
        else:
            cursor = self._con.cursor()
        cursor.execute('SELECT * FROM vips')
        rows = cursor.fetchall()
        if rows == None:
            raise exception.NotFound()
        list = []
        for row in rows:
            vs = VirtualServer()
            vs.loadFromDict(row)
            list.append(vs)
        return list

    def getServerFarms(self):
        self._con.row_factory = sqlite3.Row
        if DATABASE_TYPE == 'mysql':
            cursor = self._con.cursor(mdb.cursors.DictCursor)
        else:
            cursor = self._con.cursor()
        cursor.execute('SELECT * FROM serverfarms')
        rows = cursor.fetchall()
        if rows == None:
            raise exception.NotFound()
        list = []
        for row in rows:
            sf = ServerFarm()
            sf.loadFromDict(row)
            list.append(sf)
        return list

    def getVLANbyId(self, id):
        self._con.row_factory = sqlite3.Row
        if DATABASE_TYPE == 'mysql':
            cursor = self._con.cursor(mdb.cursors.DictCursor)
        else:
            cursor = self._con.cursor()
        cursor.execute('SELECT * FROM vlans WHERE id = "%s"' % id)
        row = cursor.fetchone()
        if row == None:
            raise exception.NotFound()
        vlan = VLAN()
        vlan.loadFromDict(row)
        return vlan

    def getVLANs(self):
        self._con.row_factory = sqlite3.Row
        if DATABASE_TYPE == 'mysql':
            cursor = self._con.cursor(mdb.cursors.DictCursor)
        else:
            cursor = self._con.cursor()
        cursor.execute('SELECT * FROM vlans')
        rows = cursor.fetchall()
        if rows == None:
            raise exception.NotFound()
        list = []
        for row in rows:
            vlan = VLAN()
            vlan.loadFromDict(row)
            list.append(vlan)
        return list

    def getSFByLBid(self,  id):
        self._con.row_factory = sqlite3.Row
        if DATABASE_TYPE == 'mysql':
            cursor = self._con.cursor(mdb.cursors.DictCursor)
        else:
            cursor = self._con.cursor()
        cursor.execute('SELECT * FROM loadbalancers WHERE id = "%s"' % id)
        dict = cursor.fetchone()
        cursor.execute('SELECT * FROM serverfarms WHERE lb_id = "%s"' % \
                                                              dict['id'])
        row = cursor.fetchone()
        sf = ServerFarm()
        sf.loadFromDict(row)
        return sf

    def getRServersBySFid(self, id):
        self._con.row_factory = sqlite3.Row
        if DATABASE_TYPE == 'mysql':
            cursor = self._con.cursor(mdb.cursors.DictCursor)
        else:
            cursor = self._con.cursor()
        cursor.execute('SELECT * FROM rservers WHERE sf_id = "%s"' % id)
        rows = cursor.fetchall()
        list = []
        for row in rows:
            rs = RealServer()
            rs.loadFromDict(row)
            list.append(rs)
        return list

    def getStickiesBySFid(self, id):
        self._con.row_factory = sqlite3.Row
        if DATABASE_TYPE == 'mysql':
            cursor = self._con.cursor(mdb.cursors.DictCursor)
        else:
            cursor = self._con.cursor()
        cursor.execute('SELECT * FROM stickies WHERE sf_id = "%s"' % id)
        rows = cursor.fetchall()
        list = []
        for row in rows:
            st = self._stickyDict[row['type']].createSame()
            st.loadFromDict(row)
            list.append(st)
        return list
        
    def getProbesBySFid(self, id):
        self._con.row_factory = sqlite3.Row
        if DATABASE_TYPE == 'mysql':
            cursor = self._con.cursor(mdb.cursors.DictCursor)
        else:
            cursor = self._con.cursor()
        cursor.execute('SELECT * FROM probes WHERE sf_id = "%s"' % id)
        rows = cursor.fetchall()
        list = []
        for row in rows:
            pr = self._probeDict[row['type']].createSame()
            pr.loadFromDict(row)
            list.append(pr)
        return list

    def getPredictorBySFid(self, id):
        self._con.row_factory = sqlite3.Row
        if DATABASE_TYPE == 'mysql':
            cursor = self._con.cursor(mdb.cursors.DictCursor)
        else:
            cursor = self._con.cursor()
        cursor.execute('SELECT * FROM predictors WHERE sf_id = "%s"' % id)
        rows = cursor.fetchone()
        pred = self._predictDict[rows['type']].createSame()
        pred.loadFromDict(rows)
        return pred

    def getVIPsBySFid(self, id):
        self._con.row_factory = sqlite3.Row
        if DATABASE_TYPE == 'mysql':
            cursor = self._con.cursor(mdb.cursors.DictCursor)
        else:
            cursor = self._con.cursor()
        cursor.execute('SELECT * FROM vips WHERE sf_id = "%s"' % id)
        rows = cursor.fetchall()
        list = []
        for row in rows:
            vs = VirtualServer()
            vs.loadFromDict(row)
            list.append(vs)
        return list


class Writer(SQLExecute):
    def __init__(self,  db):
        logger.debug("Writer: connecting to db: %s" % db)
        if DATABASE_TYPE =='mysql':
            self._con = mdb.connect('localhost',  'root',  'swordfish',  'balancer')
        else:
            self._con = sqlite3.connect(db)
    
             

    def writeLoadBalancer(self,  lb):
        logger.debug("Saving LoadBalancer instance in DB.")
        if DATABASE_TYPE == 'mysql':
            cursor = self._con.cursor(mdb.cursors.DictCursor)
        else:
            cursor = self._con.cursor()
        dict = lb.convertToDict()
        command = self.generateCommand("INSERT INTO loadbalancers (", dict)
        msg = "Executing command: %s" % command
        logger.debug(msg)
        self.execute(cursor, command)
        self._con.commit()

    def writeDevice(self,  device):
        logger.debug("Saving Device instance in DB.")
        if DATABASE_TYPE == 'mysql':
            cursor = self._con.cursor(mdb.cursors.DictCursor)
        else:
            cursor = self._con.cursor()
        dict = device.convertToDict()
        command = self.generateCommand(" INSERT INTO devices (", dict)
        msg = "Executing command: %s" % command
        logger.debug(msg)
        self.execute(cursor, command)
        self._con.commit()

    def writeProbe(self, prb):
        logger.debug("Saving Probe instance in DB.")
        if DATABASE_TYPE == 'mysql':
            cursor = self._con.cursor(mdb.cursors.DictCursor)
        else:
            cursor = self._con.cursor()
        dict = prb.convertToDict()
        command = self.generateCommand(" INSERT INTO probes (", dict)
        msg = "Executing command: %s" % command
        logger.debug(msg)
        self.execute(cursor, command)
        self._con.commit()
        
    def writeSticky(self, st):
        if st == None:
            return
        logger.debug("Saving Sticky instance in DB.")
        if DATABASE_TYPE == 'mysql':
            cursor = self._con.cursor(mdb.cursors.DictCursor)
        else:
            cursor = self._con.cursor()
        dict = st.convertToDict()
        command = self.generateCommand(" INSERT INTO stickies (", dict)
        msg = "Executing command: %s" % command
        logger.debug(msg)
        self.execute(cursor, command)
        self._con.commit()

    def generateCommand(self, start, dict):
        command1 = start
        command2 = ""
        i = 0
        for key in dict.keys():
            if i < len(dict) - 1:
                command1 += key + ','
                command2 += "'" + str(dict[key]) + "'" + ","
            else:
                command1 += key + ") VALUES("
                command2 += "'" + str(dict[key]) + "'" + ");"
            i += 1
        command = command1 + command2
        return command

    def writeRServer(self,  rs):
        logger.debug("Saving RServer instance in DB.")
        if DATABASE_TYPE == 'mysql':
            cursor = self._con.cursor(mdb.cursors.DictCursor)
        else:
            cursor = self._con.cursor()
        dict = rs.convertToDict()
        command = self.generateCommand(" INSERT INTO rservers (", dict)
        msg = "Executing command: %s" % command
        logger.debug(msg)
        self.execute(cursor, command)
        self._con.commit()

    def writePredictor(self, prd):
        logger.debug("Saving Predictor instance in DB.")
        if DATABASE_TYPE == 'mysql':
            cursor = self._con.cursor(mdb.cursors.DictCursor)
        else:
            cursor = self._con.cursor()
        dict = prd.convertToDict()
        command = self.generateCommand("INSERT INTO predictors (", dict)
        msg = "Executing command: %s" % command
        logger.debug(msg)
        self.execute(cursor, command)
        self._con.commit()

    def writeServerFarm(self, sf):
        logger.debug("Saving ServerFarm instance in DB.")
        if DATABASE_TYPE == 'mysql':
            cursor = self._con.cursor(mdb.cursors.DictCursor)
        else:
            cursor = self._con.cursor()
        dict = sf.convertToDict()
        command = self.generateCommand("INSERT INTO serverfarms (", dict)
        msg = "Executing command: %s" % command
        logger.debug(msg)
        self.execute(cursor, command)
        self._con.commit()

    def writeVirtualServer(self, vs):
        logger.debug("Saving VirtualServer instance in DB.")
        if DATABASE_TYPE == 'mysql':
            cursor = self._con.cursor(mdb.cursors.DictCursor)
        else:
            cursor = self._con.cursor()
        dict = vs.convertToDict()
        command = self.generateCommand("INSERT INTO vips (", dict)
        msg = "Executing command: %s" % command
        logger.debug(msg)
        self.execute(cursor, command)
        self._con.commit()

    def writeVLAN(self, vlan):
        logger.debug("Saving VLAN instance in DB.")
        if DATABASE_TYPE == 'mysql':
            cursor = self._con.cursor(mdb.cursors.DictCursor)
        else:
            cursor = self._con.cursor()
        dict = vlan.convertToDict()
        command = self.generateCommand("INSERT INTO vlans (", dict)
        msg = "Executing command: %s" % command
        logger.debug(msg)
        self.execute(cursor, command)
        self._con.commit()

    def getTableForObject(self,  obj):
        table = ""
        if isinstance(obj, LoadBalancer):
            table = "loadbalancers"
        elif isinstance(obj, ServerFarm):
            table = "serverfarms"
        elif isinstance(obj,  BasePredictor):
            table = "predictors"
        elif isinstance(obj,  RealServer):
            table = "rservers"
        elif isinstance(obj,  LBDevice):
            table = "devices"
        elif isinstance(obj,  VirtualServer):
            table = "vips"
        elif isinstance(obj,  VLAN):
            table = "vlans"
        elif isinstance(obj, Probe):
            table = "probes"
        elif isinstance(obj, Sticky):
            table = "stickies"
        return table
        
    def updateObjectInTable(self,  obj):
        table = self.getTableForObject(obj)
                   
        if table != "":
            logger.debug("Updating table %s in DB." % table)
            dict = obj.convertToDict()
            command = self.generateUpdateCommand(table,  dict,  obj.id)
            if DATABASE_TYPE == 'mysql':
                cursor = self._con.cursor(mdb.cursors.DictCursor)
            else:
                cursor = self._con.cursor()
            logger.debug("Executing command: %s" % command)
            self.execute(cursor, command)
        self._con.commit()

    def updateDeployed(self,  obj,  status):
            table = self.getTableForObject(obj)
            if DATABASE_TYPE == 'mysql':
                cursor = self._con.cursor(mdb.cursors.DictCursor)
            else:
                cursor = self._con.cursor()
            cursor.execute("UPDATE %s SET deployed='%s' WHERE id='%s'" % (table, status, obj.id))
            self._con.commit()
        
    def generateUpdateCommand(self,  table, dict,  id):
        command1 = "UPDATE %s SET " % table

        i = 0
        for key in dict.keys():
            if i < len(dict) - 1:
                if key != "id":
                    command1 += key + '=\"' + str(dict[key]) + '\",'

            else:
                if key != "id":
                    command1 += key + '=\"' + str(dict[key]) + '\"'
            i += 1
        command = command1 + " WHERE id = '" + str(id) + "'"
        return command


class Deleter(SQLExecute):
    def __init__(self,  db):
        logger.debug("Deleter: connecting to db: %s" % db)
        if DATABASE_TYPE =='mysql':
            self._con = mdb.connect('localhost',  'root',  'swordfish',  'balancer')
        else:
            self._con = sqlite3.connect(db)

    def deleteRSbyID(self, id):
        if DATABASE_TYPE == 'mysql':
            cursor = self._con.cursor(mdb.cursors.DictCursor)
        else:
            cursor = self._con.cursor()
        command = "DELETE from rservers where id = '%s'" % id
        msg = "Executing command: %s" % command
        logger.debug(msg)
        self.execute(cursor, command)
        self._con.commit()

    def deleteRSsBySFid(self, id):
        if DATABASE_TYPE == 'mysql':
            cursor = self._con.cursor(mdb.cursors.DictCursor)
        else:
            cursor = self._con.cursor()
        command = "DELETE from rservers where  sf_id = '%s'" % id
        msg = "Executing command: %s" % command
        logger.debug(msg)
        self.execute(cursor, command)
        self._con.commit()

    def deleteVSbyID(self, id):
        if DATABASE_TYPE == 'mysql':
            cursor = self._con.cursor(mdb.cursors.DictCursor)
        else:
            cursor = self._con.cursor()
        command = "DELETE from vips where id = '%s'" % id
        msg = "Executing command: %s" % command
        logger.debug(msg)
        self.execute(cursor, command)
        self._con.commit()

    def deleteVSsBySFid(self,  id):
        if DATABASE_TYPE == 'mysql':
            cursor = self._con.cursor(mdb.cursors.DictCursor)
        else:
            cursor = self._con.cursor()
        command = "DELETE from vips where  sf_id = '%s'" % id
        msg = "Executing command: %s" % command
        logger.debug(msg)
        self.execute(cursor, command)
        self._con.commit()

    def deleteProbeByID(self,  id):
        if DATABASE_TYPE == 'mysql':
            cursor = self._con.cursor(mdb.cursors.DictCursor)
        else:
            cursor = self._con.cursor()
        command = "DELETE from probes where id = '%s'" % id
        msg = "Executing command: %s" % command
        logger.debug(msg)
        self.execute(cursor, command)
        self._con.commit()

    def deleteProbesBySFid(self, id):
        if DATABASE_TYPE == 'mysql':
            cursor = self._con.cursor(mdb.cursors.DictCursor)
        else:
            cursor = self._con.cursor()
        command = "DELETE from probes where probes.sf_id = '%s'" % id
        msg = "Executing command: %s" % command
        logger.debug(msg)
        self.execute(cursor, command)
        self._con.commit()

    def deleteStickyByID(self,  id):
        if DATABASE_TYPE == 'mysql':
            cursor = self._con.cursor(mdb.cursors.DictCursor)
        else:
            cursor = self._con.cursor()
        command = "DELETE from stickies where id = '%s'" % id
        msg = "Executing command: %s" % command
        logger.debug(msg)
        self.execute(cursor, command)
        self._con.commit()

    def deleteStickiesBySFid(self, id):
        if DATABASE_TYPE == 'mysql':
            cursor = self._con.cursor(mdb.cursors.DictCursor)
        else:
            cursor = self._con.cursor()
        command = "DELETE from stickies where sf_id = '%s'" % id
        msg = "Executing command: %s" % command
        logger.debug(msg)
        self.execute(cursor, command)
        self._con.commit()

    def deleteLBbyID(self,  id):
        if DATABASE_TYPE == 'mysql':
            cursor = self._con.cursor(mdb.cursors.DictCursor)
        else:
            cursor = self._con.cursor()
        command = "DELETE from loadbalancers where id = '%s'" % id
        msg = "Executing command: %s" % command
        logger.debug(msg)
        self.execute(cursor, command)
        self._con.commit()

    def deleteDeviceByID(self, id):
        if DATABASE_TYPE == 'mysql':
            cursor = self._con.cursor(mdb.cursors.DictCursor)
        else:
            cursor = self._con.cursor()
        command = "DELETE from devices where id = '%s'" % id
        msg = "Executing command: %s" % command
        logger.debug(msg)
        self.execute(cursor, command)
        self._con.commit()

    def deletePredictorByID(self, id):
        if DATABASE_TYPE == 'mysql':
            cursor = self._con.cursor(mdb.cursors.DictCursor)
        else:
            cursor = self._con.cursor()
        command = "DELETE from predictors where id = '%s'" % id
        msg = "Executing command: %s" % command
        logger.debug(msg)
        self.execute(cursor, command)
        self._con.commit()

    def deletePredictorBySFid(self, id):
        if DATABASE_TYPE == 'mysql':
            cursor = self._con.cursor(mdb.cursors.DictCursor)
        else:
            cursor = self._con.cursor()
        command = "DELETE from predictors where sf_id = '%s'" % id
        msg = "Executing command: %s" % command
        logger.debug(msg)
        self.execute(cursor, command)
        self._con.commit()

    def deleteSFbyID(self, id):
        if DATABASE_TYPE == 'mysql':
            cursor = self._con.cursor(mdb.cursors.DictCursor)
        else:
            cursor = self._con.cursor()
        command = "DELETE from serverfarms where id = '%s'" % id
        msg = "Executing command: %s" % command
        logger.debug(msg)
        self.execute(cursor, command)
        self._con.commit()

    def deleteSFbyLBid(self, id):
        if DATABASE_TYPE == 'mysql':
            cursor = self._con.cursor(mdb.cursors.DictCursor)
        else:
            cursor = self._con.cursor()
        command = "DELETE from serverfarms where lb_id = '%s'" % id
        msg = "Executing command: %s" % command
        logger.debug(msg)
        self.execute(cursor, command)
        self._con.commit()

    def deleteVLANbyID(self,  id):
        if DATABASE_TYPE == 'mysql':
            cursor = self._con.cursor(mdb.cursors.DictCursor)
        else:
            cursor = self._con.cursor()
        command = "DELETE from vlans where id = '%s'" % id
        msg = "Executing command: %s" % command
        logger.debug(msg)
        self.execute(cursor, command)
        self._con.commit()


class Storage(object):
    def __init__(self,  conf=None):
        db = None
        if conf == None:
            conf_data = Configuration.Instance()
            conf = conf_data.get()
            if isinstance(conf,  dict):
                db = conf['db_path']
            else:
                db = conf.db_path                
        else:
            db = conf['db_path']
        self._db = db
        self._writer = Writer(self._db)

    def getReader(self):
        return Reader(self._db)

    def getWriter(self):
        return self._writer

    def getDeleter(self):
        return Deleter(self._db)
