"""Test fetch together with NFN"""

import abc
import os
import shutil
import time
import unittest
import base64
import platform

from PiCN.ProgramLibs.Fetch import Fetch
from PiCN.ProgramLibs.NFNForwarder import NFNForwarder

from PiCN.Mgmt import MgmtClient
from PiCN.Packets import Name, Nack, Content
from PiCN.ProgramLibs.ICNDataRepository import ICNDataRepository
from PiCN.Layers.PacketEncodingLayer.Encoder import SimpleStringEncoder, NdnTlvEncoder
from PiCN.Layers.NFNLayer.NFNExecutor import NFNPythonExecutor, x86Executor

class cases_FetchNFN(object):

    @abc.abstractmethod
    def get_encoder(self):
        """get the packet encoder to be used"""

    def setUp(self):
        self.data1 = "data1"
        self.data2 = 'a' * 5000
        self.data3 = 'b' * 20000

        self.path = "/tmp/repo_unit_test"
        try:
            os.stat(self.path)
        except:
            os.mkdir(self.path)
        with open(self.path + "/d1", 'w+') as content_file:
            content_file.write(self.data1)
        with open(self.path + "/d2", 'w+') as content_file:
            content_file.write(self.data2)
        with open(self.path + "/d3", 'w+') as content_file:
            content_file.write('b' * 20000)

        self.ICNRepo: ICNDataRepository = ICNDataRepository("/tmp/repo_unit_test", Name("/test/data"), 0,
                                                            encoder=self.get_encoder(), log_level=255)
        self.forwarder1: NFNForwarder = NFNForwarder(0, log_level=255, encoder=self.get_encoder())
        self.forwarder2: NFNForwarder = NFNForwarder(0, log_level=255, encoder=self.get_encoder())

        self.repo_port = self.ICNRepo.linklayer.interfaces[0].get_port()
        self.fwd_port1 = self.forwarder1.linklayer.interfaces[0].get_port()
        self.fwd_port2 = self.forwarder2.linklayer.interfaces[0].get_port()

        self.fetch = Fetch("127.0.0.1", self.fwd_port1, encoder=self.get_encoder())

    def add_face_and_forwadingrule(self):
        #create new face
        self.mgmtClient1 = MgmtClient(self.fwd_port1)
        self.mgmtClient1.add_face("127.0.0.1", self.fwd_port2, 0)
        self.mgmtClient1.add_forwarding_rule(Name("/lib"), [0])
        self.mgmtClient1.add_face("127.0.0.1", self.repo_port, 0)
        self.mgmtClient1.add_forwarding_rule(Name("/test"), [0])

        self.mgmtClient2 = MgmtClient(self.fwd_port2)
        self.mgmtClient2.add_face("127.0.0.1", self.repo_port, 0)
        self.mgmtClient2.add_forwarding_rule(Name("/test"), [0])

    def tearDown(self):
        try:
            shutil.rmtree(self.path)
            os.remove(self.path)
        except:
            pass
        try:
            self.mgmtClient1.shutdown()
            self.mgmtClient2.shutdown()
            self.ICNRepo.stop_repo()
            self.forwarder1.stop_forwarder()
            self.forwarder2.stop_forwarder()
            self.fetch.stop_fetch()
        except:
            pass

    def test_fetch_single_data_from_repo_over_forwarder(self):
        """Test fetch data from repo over forwarder"""
        self.ICNRepo.start_repo()
        self.forwarder1.start_forwarder()
        self.forwarder2.start_forwarder()
        time.sleep(2)
        self.add_face_and_forwadingrule()
        time.sleep(5)
        fetch_name = "/test/data/d1"
        try:
            content = None
            while content is None or content == 'Received Nack: no forwarding rule':
                content = self.fetch.fetch_data(fetch_name, timeout=20)
        except:
            self.fail
        self.assertEqual(self.data1, content)

    def test_fetch_chunked_data_from_repo_over_forwarder(self):
        """Test fetch chunked data from repo over forwarder"""
        self.ICNRepo.start_repo()
        self.forwarder1.start_forwarder()
        self.forwarder2.start_forwarder()
        time.sleep(2)
        self.add_face_and_forwadingrule()
        time.sleep(5)
        fetch_name = "/test/data/d3"
        content = None
        while content is None or content == 'Received Nack: no forwarding rule':
            content = self.fetch.fetch_data(fetch_name, timeout=20)
        self.assertEqual(self.data3, content)

    def test_compute_on_single_data_over_forwarder(self):
        """Test fetch result with single input data"""
        self.ICNRepo.start_repo()
        self.forwarder1.start_forwarder()
        self.forwarder2.start_forwarder()
        time.sleep(2)
        self.add_face_and_forwadingrule()
        time.sleep(5)
        self.mgmtClient1.add_new_content(Name("/test/data/d1"), self.data1)
        self.mgmtClient2.add_new_content(Name("/lib/func/f1"), "PYTHON\nf\ndef f(a):\n    return a.upper()")
        fetch_name = Name("/lib/func/f1")
        fetch_name += "_(/test/data/d1)"
        fetch_name += "NFN"
        try:
            content = None
            while content is None or content == 'Received Nack: no forwarding rule':
                content = self.fetch.fetch_data(fetch_name, timeout=20)
        except:
            self.fail()
        self.assertEqual(self.data1.upper(), content)

    def test_compute_on_single_data_over_forwarder_data_from_repo(self):
        """Test fetch result with single input data from repo"""
        self.ICNRepo.start_repo()
        self.forwarder1.start_forwarder()
        self.forwarder2.start_forwarder()
        time.sleep(2)
        self.add_face_and_forwadingrule()
        time.sleep(5)
        self.mgmtClient2.add_new_content(Name("/lib/func/f1"), "PYTHON\nf\ndef f(a):\n    return a.upper()")
        fetch_name = Name("/lib/func/f1")
        fetch_name += "_(/test/data/d1)"
        fetch_name += "NFN"
        try:
            content = self.fetch.fetch_data(fetch_name, timeout=20)
        except:
            self.fail()
        self.assertEqual(self.data1.upper(), content)

    def test_compute_on_large_data_over_forwarder_data_from_repo(self):
        """Test fetch result with large input data from repo"""
        self.ICNRepo.start_repo()
        self.forwarder1.start_forwarder()
        self.forwarder2.start_forwarder()
        time.sleep(2)
        self.add_face_and_forwadingrule()
        time.sleep(5)
        self.mgmtClient2.add_new_content(Name("/lib/func/f1"), "PYTHON\nf\ndef f(a):\n    return a.upper()")
        fetch_name = Name("/lib/func/f1")
        fetch_name += "_(/test/data/d3)"
        fetch_name += "NFN"
        time.sleep(1)
        content = None
        try:
            while content is None or content == 'Received Nack: no forwarding rule':
                content = self.fetch.fetch_data(fetch_name, timeout=20)
        except:
            self.fail()
        self.assertEqual(self.data3.upper(), content)

    def test_compute_on_large_data_over_forwarder_data_from_repo_to_data_prefix(self):
        """Test fetch result with large input data from repo with a to data prefix"""
        self.ICNRepo.start_repo()
        self.forwarder1.start_forwarder()
        self.forwarder2.start_forwarder()
        time.sleep(2)
        self.add_face_and_forwadingrule()
        time.sleep(5)
        self.mgmtClient2.add_new_content(Name("/lib/func/f1"), "PYTHON\nf\ndef f(a):\n    return a.upper()")
        fetch_name = Name("/test/data/d3")
        fetch_name += "/lib/func/f1(_)"
        fetch_name += "NFN"
        time.sleep(1)
        content = None
        try:
            while content is None or content == 'Received Nack: no forwarding rule':
                content = self.fetch.fetch_data(fetch_name, timeout=20)
        except:
            self.fail()
        self.assertEqual(self.data3.upper(), content)


    def test_fetch_single_data_from_repo_over_forwarder_native_code(self):
        """Test fetch data from repo over forwarder using native code"""
        if platform.system() != 'Darwin':
            self.skipTest("Test only for OSX available")
        execs = {"PYTHON": NFNPythonExecutor(), "x86": x86Executor()}
        self.forwarder1 = NFNForwarder(0, log_level=255, encoder=self.get_encoder(), executors=execs)
        self.fwd_port1 = self.forwarder1.linklayer.interfaces[0].get_port()
        self.fetch = Fetch("127.0.0.1", self.fwd_port1, encoder=self.get_encoder())
        self.ICNRepo.start_repo()
        self.forwarder1.start_forwarder()
        self.forwarder2.start_forwarder()
        time.sleep(2)
        self.add_face_and_forwadingrule()
        nfnfile = open('NFN-x86-file-osx', 'r')
        content_obj = nfnfile.read()
        self.forwarder1.icnlayer.cs.add_content_object(Content("/func/native/test", content_obj))
        #self.mgmtClient1.add_new_content(Name("/func/native/test"), content_obj)
        time.sleep(5)
        fetch_name = Name("/func/native/test")
        fetch_name += '_("hello")'
        fetch_name += 'NFN'
        try:
            content = None
            while content is None or content == 'Received Nack: no forwarding rule':
                content = self.fetch.fetch_data(fetch_name, timeout=20)
        except:
            self.fail
        self.assertEqual("5", content)

class test_FetchNFN_SimplePacketEncoder(cases_FetchNFN, unittest.TestCase):
    """Runs tests with the SimplePacketEncoder"""
    def get_encoder(self):
        return SimpleStringEncoder()

class test_FetchNFN_NDNTLVPacketEncoder(cases_FetchNFN, unittest.TestCase):
    """Runs tests with the NDNTLVPacketEncoder"""
    def get_encoder(self):
        return NdnTlvEncoder()
