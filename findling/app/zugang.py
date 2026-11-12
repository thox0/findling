"""Erreichbarkeit im Heimnetz: ein fester Name für die QR-Codes und HTTPS für die Kopie unterwegs."""
import shutil
import subprocess
import threading
import time
from pathlib import Path

STABLE_NAME = "findling.local"
CERT_DAYS = 820  # iPhones lehnen Serverzertifikate mit mehr als 825 Tagen ab.


def _run(*arguments):
    subprocess.run(arguments, check=True, capture_output=True, timeout=60)


def certificate_paths(data_dir):
    folder = Path(data_dir) / "zertifikat"
    return {"folder": folder, "ca": folder / "findling-zertifikat.crt", "cert": folder / "server.crt", "key": folder / "server.key"}


def ensure_certificate(data_dir, extra_names=()):
    """Legt bei Bedarf ein eigenes Zertifikat an und gibt die Pfade zurück, ohne openssl None.

    Der Schlüssel der kleinen Zertifizierungsstelle wird sofort vernichtet und das Zertifikat gilt nur
    für die Namen dieser App. Auch wer die Dateien stiehlt, kann damit keine fremden Seiten fälschen.
    """
    if not shutil.which("openssl"):
        return None
    paths = certificate_paths(data_dir)
    names = list(dict.fromkeys([STABLE_NAME, "localhost", *extra_names]))
    known = paths["folder"] / "namen.txt"
    same_names = known.exists() and known.read_text().split() == names
    if same_names and paths["cert"].exists() and paths["key"].exists() and paths["ca"].exists():
        try:
            _run("openssl", "x509", "-checkend", str(30 * 86400), "-noout", "-in", str(paths["cert"]))
            return paths
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
            pass
    folder = paths["folder"]
    folder.mkdir(parents=True, exist_ok=True)
    folder.chmod(0o700)
    permitted = ",".join(f"permitted;DNS:{name}" for name in names)
    alt_names = ",".join(f"DNS:{name}" for name in names)
    config = folder / "openssl.cnf"
    config.write_text(
        "[req]\ndistinguished_name = dn\n[dn]\n"
        "[ca_ext]\nbasicConstraints = critical,CA:TRUE,pathlen:0\nkeyUsage = critical,keyCertSign,cRLSign\n"
        f"nameConstraints = critical,{permitted}\nsubjectKeyIdentifier = hash\n"
        "[leaf_ext]\nbasicConstraints = critical,CA:FALSE\nkeyUsage = critical,digitalSignature,keyEncipherment\n"
        "subjectKeyIdentifier = hash\nauthorityKeyIdentifier = keyid:always\n"
        f"extendedKeyUsage = serverAuth\nsubjectAltName = {alt_names}\n"
    )
    ca_key = folder / "ca.key"
    request = folder / "server.csr"
    serial = folder / "findling-zertifikat.srl"
    try:
        _run("openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-sha256", "-days", str(CERT_DAYS + 5),
             "-subj", "/CN=findling lokal", "-keyout", str(ca_key), "-out", str(paths["ca"]),
             "-config", str(config), "-extensions", "ca_ext")
        _run("openssl", "req", "-new", "-newkey", "rsa:2048", "-nodes", "-sha256", "-subj", f"/CN={STABLE_NAME}",
             "-keyout", str(paths["key"]), "-out", str(request), "-config", str(config))
        _run("openssl", "x509", "-req", "-sha256", "-days", str(CERT_DAYS), "-in", str(request),
             "-CA", str(paths["ca"]), "-CAkey", str(ca_key), "-CAcreateserial", "-out", str(paths["cert"]),
             "-extfile", str(config), "-extensions", "leaf_ext")
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError):
        return None
    finally:
        for leftover in (ca_key, request, serial, config):
            leftover.unlink(missing_ok=True)
    paths["key"].chmod(0o600)
    known.write_text("\n".join(names) + "\n")
    return paths


class StableName:
    """Macht die App im Heimnetz unter findling.local erreichbar, unabhängig vom Rechnernamen."""

    def __init__(self, port, get_ip):
        self.port = port
        self.get_ip = get_ip
        self.process = None
        self.ip = None
        self.stopped = threading.Event()
        self.active = bool(shutil.which("dns-sd"))

    def start(self):
        if not self.active:
            return False
        self._publish()
        threading.Thread(target=self._watch, daemon=True).start()
        return True

    def _publish(self):
        self._end_process()
        self.ip = self.get_ip()
        if self.ip.startswith("127."):
            return
        self.process = subprocess.Popen(
            ["dns-sd", "-P", "findling", "_http._tcp", "local", str(self.port), STABLE_NAME, self.ip],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )

    def _watch(self):
        # Wechselt der Mac das Netz, muss der Name auf die neue Adresse zeigen.
        while not self.stopped.wait(60):
            if self.get_ip() != self.ip or (self.process and self.process.poll() is not None):
                self._publish()

    def _end_process(self):
        if self.process:
            self.process.terminate()
            try:
                self.process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.process.kill()
            self.process = None

    def stop(self):
        self.stopped.set()
        self._end_process()
        time.sleep(0)
