#!/usr/bin/env python3
"""Offline Helm render checks; no cluster, no real credentials."""
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

import yaml

# Outside the chart directory: a tests/ pattern in .helmignore would also drop templates/tests/.
CHART = Path(__file__).resolve().parents[1] / "paperless-ai"
RELEASE = "paperless-ai"


def render(*args, fixture="ci/test-values.yaml", chart=CHART):
    command = ["helm", "template", RELEASE, str(chart), "-n", "pai"]
    if fixture:
        command += ["-f", str(CHART / fixture)]
    return subprocess.run(command + list(args), text=True, capture_output=True)


def docs_of(result):
    if result.returncode:
        raise RuntimeError(result.stderr)
    return [d for d in yaml.safe_load_all(result.stdout) if d]


def find(docs, kind):
    return [d for d in docs if d["kind"] == kind]


def sts_of(docs):
    sts = find(docs, "StatefulSet")
    assert len(sts) == 1, sts
    return sts[0]["spec"]


def env_of(container):
    return {e["name"]: e for e in container.get("env", [])}


class FixtureTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.docs = docs_of(render())
        cls.sts = sts_of(cls.docs)
        cls.pod = cls.sts["template"]["spec"]
        cls.main = cls.pod["containers"][0]
        cls.env = env_of(cls.main)

    def test_single_pod_without_service_links(self):
        self.assertEqual(self.sts["replicas"], 1)
        # A Service named paperless-ai would inject PAPERLESS_AI_PORT=tcp://<ip>:3000.
        self.assertIs(self.pod["enableServiceLinks"], False)
        self.assertEqual(self.env["PAPERLESS_AI_PORT"]["value"], "3000")

    def test_service_port_maps_to_fixed_container_port(self):
        # The fixture sets service.port 80; the app keeps listening on 3000.
        self.assertEqual(self.main["ports"], [{"name": "http", "containerPort": 3000, "protocol": "TCP"}])
        svc = find(self.docs, "Service")[0]["spec"]["ports"][0]
        self.assertEqual((svc["port"], svc["targetPort"]), (80, "http"))
        backend = find(self.docs, "Ingress")[0]["spec"]["rules"][0]["http"]["paths"][0]["backend"]["service"]
        self.assertEqual(backend["port"]["number"], 80)
        for probe in ("startupProbe", "livenessProbe", "readinessProbe"):
            self.assertEqual(self.main[probe]["httpGet"], {"path": "/health", "port": "http"})

    def test_paperless_elsewhere_with_token_from_secret(self):
        self.assertEqual(self.env["PAPERLESS_API_URL"]["value"], "https://paperless.example.com")
        self.assertEqual(self.env["PAPERLESS_PUBLIC_URL"]["value"], "https://paperless.example.com")
        self.assertEqual(self.env["PAPERLESS_API_TOKEN"]["valueFrom"]["secretKeyRef"],
                         {"name": "example-paperless-token", "key": "api-token"})
        self.assertEqual(self.pod["hostAliases"][0]["hostnames"], ["paperless.example.com"])

    def test_own_ca_mounted_for_node(self):
        self.assertEqual(self.env["NODE_EXTRA_CA_CERTS"]["value"], "/etc/paperless-ai/ca/ca.crt")
        mounts = {m["name"]: m["mountPath"] for m in self.main["volumeMounts"]}
        self.assertEqual(mounts["ca"], "/etc/paperless-ai/ca")
        ca = [v for v in self.pod["volumes"] if v["name"] == "ca"][0]
        self.assertEqual(ca["configMap"]["name"], "example-ca")

    def test_oidc_and_proxy(self):
        self.assertEqual(self.env["OIDC_ENABLED"]["value"], "true")
        self.assertEqual(self.env["OIDC_ISSUER"]["value"], "https://sso.example.com/realms/example")
        self.assertEqual(self.env["OIDC_CLIENT_SECRET"]["valueFrom"]["secretKeyRef"],
                         {"name": "example-paperless-ai-oidc", "key": "client-secret"})
        self.assertEqual(self.env["OIDC_ALLOWED_GROUPS"]["value"], "paperless,admins")
        self.assertEqual(self.env["PASSWORD_LOGIN"]["value"], "false")
        self.assertEqual(self.env["PAPERLESS_AI_URL"]["value"], "https://paperless-ai.example.com")
        # Ingress enabled: one trusted proxy hop.
        self.assertEqual(self.env["TRUST_PROXY"]["value"], "1")

    def test_no_secret_values_rendered(self):
        self.assertEqual(find(self.docs, "Secret"), [])
        secret_like = [n for n in self.env if n.endswith(("_KEY", "_SECRET", "_TOKEN", "_PASSWORD"))]
        # The fixture has three of them; all come from Secrets.
        self.assertEqual(sorted(secret_like), ["CUSTOM_API_KEY", "OIDC_CLIENT_SECRET", "PAPERLESS_API_TOKEN"])
        for name in secret_like:
            self.assertIn("valueFrom", self.env[name], name)

    def test_runs_unprivileged_read_only(self):
        # Verified against paperless-ai 4.3.1 on Longhorn, also with a root-owned 3.x data/.env; 4.5.1 and 4.7.1
        # with the same security context in Docker (upgrades 4.3.1 → 4.5.1 and 4.5.1 → 4.7.1, each on one volume).
        self.assertEqual(self.pod["securityContext"]["runAsUser"], 1000)
        self.assertEqual(self.pod["securityContext"]["fsGroup"], 1000)
        self.assertTrue(self.main["securityContext"]["readOnlyRootFilesystem"])
        mounts = {m["mountPath"]: m["name"] for m in self.main["volumeMounts"]}
        self.assertEqual(mounts["/app/data"], "data")
        self.assertEqual(mounts["/tmp"], "tmp")


class DefaultsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.docs = docs_of(render(fixture=None))
        cls.main = sts_of(cls.docs)["template"]["spec"]["containers"][0]
        cls.env = env_of(cls.main)

    def test_image_follows_app_version(self):
        app_version = yaml.safe_load((CHART / "Chart.yaml").read_text())["appVersion"]
        self.assertEqual(self.main["image"], f"clusterzx/paperless-ai:{app_version}")

    def test_nothing_pinned_by_default(self):
        # Every variable locks its setting in the web interface; defaults leave it to the wizard.
        self.assertEqual(set(self.env), {"PAPERLESS_AI_PORT", "PAPERLESS_AI_DATA_DIR"})
        self.assertNotIn("TRUST_PROXY", self.env)

    def test_cuda_variant(self):
        main = sts_of(docs_of(render("--set", "image.variant=cuda", "--set", "image.tag=4.3.1", fixture=None)))
        self.assertEqual(main["template"]["spec"]["containers"][0]["image"], "clusterzx/paperless-ai:4.3.1-cuda")


class VolumeClaimTemplateTest(unittest.TestCase):
    def test_unchanged_across_chart_versions(self):
        # Regression: chart 0.1.x put helm.sh/chart and the app version into the claim template,
        # which is immutable – every upgrade failed with "updates to statefulset spec ... forbidden".
        with tempfile.TemporaryDirectory() as tmp:
            other = Path(tmp) / "chart"
            shutil.copytree(CHART, other)
            chart_yaml = yaml.safe_load((other / "Chart.yaml").read_text())
            chart_yaml["version"] = "99.0.0"
            chart_yaml["appVersion"] = "99.0.0"
            (other / "Chart.yaml").write_text(yaml.safe_dump(chart_yaml))
            now = sts_of(docs_of(render(fixture=None)))
            later = sts_of(docs_of(render(fixture=None, chart=other)))
        # The constellation itself: labels of the StatefulSet do change between the versions.
        self.assertNotEqual(find_labels(now), find_labels(later))
        self.assertEqual(now["volumeClaimTemplates"], later["volumeClaimTemplates"])
        self.assertEqual(now["volumeClaimTemplates"][0]["metadata"]["name"], "data")


def find_labels(sts_spec):
    return sts_spec["template"]["metadata"]["labels"]


class ValidationTest(unittest.TestCase):
    def assertFails(self, message, *args):
        result = render(*args, fixture=None)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(message, result.stderr)

    def test_secret_like_env_needs_secret_reference(self):
        for name in ("OPENAI_API_KEY", "API_KEY", "JWT_SECRET", "PAPERLESS_API_TOKEN"):
            self.assertFails(f"envs {name} must use a Secret reference",
                             "--set", f"envs[0].name={name}", "--set", "envs[0].value=x")

    def test_plain_settings_with_secret_words_allowed(self):
        args = []
        for i, (name, value) in enumerate([("TOKEN_LIMIT", "128000"), ("RESPONSE_TOKENS", "1000"),
                                           ("PASSWORD_LOGIN", "false")]):
            args += ["--set", f"envs[{i}].name={name}", "--set-string", f"envs[{i}].value={value}"]
        env = env_of(sts_of(docs_of(render(*args, fixture=None)))["template"]["spec"]["containers"][0])
        self.assertEqual(env["TOKEN_LIMIT"]["value"], "128000")
        self.assertEqual(env["PASSWORD_LOGIN"]["value"], "false")

    def test_oidc_requirements(self):
        self.assertFails("oidc.issuer is required", "--set", "oidc.enabled=true")
        self.assertFails("oidc.existingSecret is required",
                         "--set", "oidc.enabled=true", "--set", "oidc.issuer=https://sso.example.com")
        self.assertFails("publicUrl is required",
                         "--set", "oidc.enabled=true", "--set", "oidc.issuer=https://sso.example.com",
                         "--set", "oidc.existingSecret=x")

    def test_variant_and_ca(self):
        self.assertFails("image.variant must be cpu or cuda", "--set", "image.variant=rocm")
        self.assertFails("extraCaCerts: set either configMap or secret",
                         "--set", "extraCaCerts.configMap=a", "--set", "extraCaCerts.secret=b")


if __name__ == "__main__":
    unittest.main(verbosity=1)
