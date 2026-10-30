"""Real loopback TLS transport with an ephemeral in-test certificate/key.

No certificate or private key is committed or shipped. This is an isolated
owner-approval simulation, never proof of pairing with a physical KRISHNA PC.
"""
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import ssl
import tempfile
import threading
import time
import unittest
from suryadev_pairing_bootstrap import request_pairing, activate_pairing, CONFIG, TOKEN


class PairingLiveTLSTests(unittest.TestCase):
    def test_real_tls_pin_owner_approval_and_device_credential(self):
        try:
            from cryptography import x509
            from cryptography.hazmat.primitives import hashes, serialization
            from cryptography.hazmat.primitives.asymmetric import rsa
            from cryptography.x509.oid import NameOID
        except ImportError:
            self.skipTest('Optional cryptography is required for ephemeral TLS test certificates')
        from datetime import datetime, timedelta, timezone
        import ipaddress
        temporary=tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        fixtures=Path(temporary.name)
        key=rsa.generate_private_key(public_exponent=65537,key_size=2048)
        name=x509.Name([x509.NameAttribute(NameOID.COMMON_NAME,'Ephemeral SURYADEV loopback test')])
        now=datetime.now(timezone.utc)
        certificate=(x509.CertificateBuilder().subject_name(name).issuer_name(name)
            .public_key(key.public_key()).serial_number(x509.random_serial_number())
            .not_valid_before(now-timedelta(minutes=1)).not_valid_after(now+timedelta(hours=1))
            .add_extension(x509.SubjectAlternativeName([x509.IPAddress(ipaddress.ip_address('127.0.0.1'))]),critical=False)
            .sign(key,hashes.SHA256()))
        (fixtures/'localhost-cert.fixture').write_bytes(certificate.public_bytes(serialization.Encoding.PEM))
        (fixtures/'localhost-key.fixture').write_bytes(key.private_bytes(serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,serialization.NoEncryption()))
        state={'approved':False,'requests':[], 'hash':None,'device':None}
        class Handler(BaseHTTPRequestHandler):
            def reply(self,code,value):
                data=json.dumps(value).encode()
                self.send_response(code); self.send_header('Content-Length',str(len(data)))
                self.send_header('Content-Type','application/json'); self.end_headers(); self.wfile.write(data)
            def do_POST(self):
                raw=self.rfile.read(int(self.headers['Content-Length']))
                state['requests'].append(('POST',raw,dict(self.headers)))
                data=json.loads(raw)
                state['hash']=data['credential_sha256']; state['device']=data['device_id']
                self.reply(200,{'request_id':'LOOPBACK-ONLY','device_id':state['device'],'expires_at':int(time.time())+600})
            def do_GET(self):
                token=self.headers.get('Authorization','').removeprefix('Device ')
                state['requests'].append(('GET',b'',dict(self.headers)))
                valid=(self.headers.get('X-Krishna-Device')==state['device'] and
                    hashlib.sha256(token.encode()).hexdigest()==state['hash'])
                if not state['approved'] or not valid:
                    self.reply(401,{'error':'paired Suryadev device required'})
                else:
                    self.reply(404,{'error':'Suryadev node has not sent a heartbeat yet'})
            def log_message(self,*args): pass
        server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        context=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.minimum_version=ssl.TLSVersion.TLSv1_2
        context.load_cert_chain(fixtures/'localhost-cert.fixture',fixtures/'localhost-key.fixture')
        server.socket=context.wrap_socket(server.socket,server_side=True)
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        pem=(fixtures/'localhost-cert.fixture').read_text()
        pin=hashlib.sha256(ssl.PEM_cert_to_DER_cert(pem)).hexdigest()
        origin='https://127.0.0.1:'+str(server.server_port)
        try:
            with tempfile.TemporaryDirectory() as folder:
                root=Path(folder)
                with self.assertRaises(ssl.SSLError):
                    request_pairing(root,origin,'0'*64,'suryadev-tls-test')
                self.assertEqual(state['requests'],[])
                self.assertFalse((root/TOKEN).exists())
                result=request_pairing(root,origin,pin,'suryadev-tls-test')
                self.assertEqual(result['state'],'owner_approval_required')
                token=(root/TOKEN).read_text().strip()
                self.assertNotIn(token,state['requests'][0][1].decode())
                self.assertEqual(state['hash'],hashlib.sha256(token.encode()).hexdigest())
                with self.assertRaises(PermissionError): activate_pairing(root)
                self.assertFalse((root/CONFIG).exists())
                # Test server simulates a separate owner's approval.
                state['approved']=True
                result=activate_pairing(root)
                self.assertEqual(result['state'],'paired_configuration_active')
                self.assertTrue((root/CONFIG).is_file())
                self.assertFalse(result['live_network_heartbeat_verified'])
                self.assertFalse(result['rishi_exam_verified'])
        finally:
            server.shutdown();server.server_close();thread.join(timeout=5)


if __name__=='__main__': unittest.main()
