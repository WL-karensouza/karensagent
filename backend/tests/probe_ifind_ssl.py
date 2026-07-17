"""
实验 11：SSL 证书验证安全评估 (H7.3)

评估 verify=False 的安全风险和可用替代方案。

测试:
  1. verify=True 能否连接成功（证书是否有效）
  2. 如果失败，提取证书信息进行风险评估
  3. 给出安全改进建议
"""
import json
import os
import sys
import ssl
import socket
from pathlib import Path
from datetime import datetime
from urllib.parse import urlparse

BACKEND_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BACKEND_DIR))

env_path = BACKEND_DIR / ".env"
if env_path.exists():
    with open(env_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            key, _, value = line.partition("=")
            if key and value:
                os.environ.setdefault(key.strip(), value.strip().strip("\"'"))

import requests
from ifind_call import SERVERS, AUTH_TOKEN, _init, _sessions

OUTPUT_DIR = Path(__file__).parent / "probe_results"
OUTPUT_DIR.mkdir(exist_ok=True)

# iFind API 域名
HOST = "api-mcp.51ifind.com"
PORT = 8643


def check_ssl_certificate():
    """通过 socket + ssl 获取证书信息"""
    print(f"\n🔒 检查 SSL 证书: {HOST}:{PORT}")

    try:
        ctx = ssl.create_default_context()
        with socket.create_connection((HOST, PORT), timeout=15) as sock:
            with ctx.wrap_socket(sock, server_hostname=HOST) as ssock:
                cert = ssock.getpeercert()

                if cert:
                    print(f"  ✅ 证书获取成功")
                    print(f"    subject: {cert.get('subject', 'N/A')}")
                    print(f"    issuer: {cert.get('issuer', 'N/A')}")
                    print(f"    notBefore: {cert.get('notBefore', 'N/A')}")
                    print(f"    notAfter: {cert.get('notAfter', 'N/A')}")
                    print(f"    SAN: {cert.get('subjectAltName', 'N/A')}")

                    # 检查有效期
                    from datetime import datetime as dt
                    not_after = dt.strptime(cert['notAfter'], "%b %d %H:%M:%S %Y %Z")
                    remaining = (not_after - dt.now()).days
                    print(f"    剩余有效期: {remaining} 天")

                    return {
                        "ok": True,
                        "subject": str(cert.get("subject", "")),
                        "issuer": str(cert.get("issuer", "")),
                        "not_before": cert.get("notBefore", ""),
                        "not_after": cert.get("notAfter", ""),
                        "san": str(cert.get("subjectAltName", "")),
                        "remaining_days": remaining,
                    }
    except ssl.SSLError as e:
        print(f"  ❌ SSL 错误: {e}")
        return {"ok": False, "ssl_error": str(e)}
    except Exception as e:
        print(f"  ❌ 连接错误: {e}")
        return {"ok": False, "error": str(e)}


def test_verify_enabled():
    """测试 verify=True 能否连接"""
    print(f"\n🧪 测试 verify=True 连接...")

    url = SERVERS["stock"]
    payload = {
        "jsonrpc": "2.0",
        "id": 999,
        "method": "initialize",
        "params": {
            "protocolVersion": "2025-03-26",
            "capabilities": {},
            "clientInfo": {"name": "ssl-test", "version": "1.0.0"},
        },
    }
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
        "Authorization": AUTH_TOKEN,
    }

    results = {}

    for verify_mode, label in [(True, "verify=True"), (False, "verify=False")]:
        try:
            resp = requests.post(
                url, json=payload, headers=headers,
                verify=verify_mode, timeout=15,
            )
            results[label] = {
                "ok": True,
                "status_code": resp.status_code,
                "session_id": resp.headers.get("Mcp-Session-Id", "N/A"),
            }
            print(f"  {label}: ✅ status={resp.status_code}, session={resp.headers.get('Mcp-Session-Id', 'N/A')}")
        except requests.exceptions.SSLError as e:
            results[label] = {"ok": False, "error": str(e)[:200]}
            print(f"  {label}: ❌ SSL错误: {str(e)[:200]}")
        except Exception as e:
            results[label] = {"ok": False, "error": str(e)[:200]}
            print(f"  {label}: ❌ {str(e)[:200]}")

    return results


def test_certifi_bundle():
    """测试使用 certifi 证书包是否能验证成功"""
    print(f"\n🧪 测试 certifi CA bundle...")
    try:
        import certifi
        ca_bundle = certifi.where()
        print(f"  certifi CA bundle: {ca_bundle}")

        url = SERVERS["stock"]
        payload = {
            "jsonrpc": "2.0",
            "id": 998,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-03-26",
                "capabilities": {},
                "clientInfo": {"name": "ssl-test2", "version": "1.0.0"},
            },
        }
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            "Authorization": AUTH_TOKEN,
        }

        try:
            resp = requests.post(
                url, json=payload, headers=headers,
                verify=ca_bundle, timeout=15,
            )
            print(f"  ✅ verify=certifi OK, status={resp.status_code}")
            return {"ok": True, "ca_bundle": ca_bundle}
        except requests.exceptions.SSLError as e:
            print(f"  ❌ verify=certifi FAILED: {str(e)[:200]}")
            return {"ok": False, "error": str(e)[:200], "ca_bundle": ca_bundle}
    except ImportError:
        print(f"  ⚠️ certifi 未安装，跳过")
        return {"ok": False, "error": "certifi not installed"}


def main():
    print("=" * 60)
    print("实验 11：SSL 证书验证安全评估")
    print(f"时间: {datetime.now().isoformat()}")
    print(f"目标: {HOST}:{PORT}")
    print("=" * 60)

    findings = {}

    # ── 1. 证书信息 ──
    print("\n📜 Part 1: 获取 SSL 证书信息")
    cert_info = check_ssl_certificate()
    findings["certificate"] = cert_info

    # ── 2. verify=True 测试 ──
    print("\n📜 Part 2: 测试 verify=True vs verify=False")
    verify_results = test_verify_enabled()
    findings["verify_test"] = verify_results

    # ── 3. certifi 测试 ──
    print("\n📜 Part 3: 测试 certifi CA bundle")
    certifi_result = test_certifi_bundle()
    findings["certifi_test"] = certifi_result

    # ── 风险评估 ──
    print("\n" + "=" * 60)
    print("📋 风险评估")
    print("=" * 60)

    verify_true_ok = verify_results.get("verify=True", {}).get("ok", False)
    verify_false_ok = verify_results.get("verify=False", {}).get("ok", False)
    cert_ok = cert_info.get("ok", False)
    certifi_ok = certifi_result.get("ok", False)

    # 风险矩阵
    risks = []
    mitigations = []

    if not verify_true_ok:
        risks.append({
            "severity": "中",
            "finding": "verify=True 无法连接 iFind API（证书验证失败）",
            "impact": "无法使用标准 SSL 验证，依赖 verify=False",
        })
        if cert_ok and cert_info.get("remaining_days", 0) > 0:
            mitigations.append("证书本身有效但可能不是公共 CA 签发，可手动添加证书到信任链")
    else:
        risks.append({
            "severity": "低",
            "finding": "verify=True 可成功连接，无需特殊处理",
            "impact": "无",
        })

    if verify_false_ok and not verify_true_ok:
        risks.append({
            "severity": "高",
            "finding": "当前使用 verify=False 跳过证书验证",
            "impact": "中间人攻击风险：攻击者可伪造 iFind API 响应，注入虚假行情数据或窃取 auth_token",
        })
        mitigations.append("方案A: 导出 iFind 服务器证书，添加到 requests 的 verify 参数指向该证书")
        mitigations.append("方案B: 通过 VPN/专线连接 iFind API，在网络层保障安全")
        mitigations.append("方案C: 如果有 HTTP 端口，考虑使用 HTTP + IP 白名单（同花顺是否支持？）")

    # 证书有效期
    if cert_ok:
        remaining = cert_info.get("remaining_days", 0)
        if remaining < 30:
            risks.append({
                "severity": "中",
                "finding": f"SSL 证书仅剩 {remaining} 天有效期",
                "impact": "证书过期后服务将不可用",
            })
        else:
            print(f"  ✅ 证书有效期: {remaining} 天（正常）")

    # ── 输出风险 ──
    for r in risks:
        print(f"\n  [{r['severity']}风险] {r['finding']}")
        print(f"   影响: {r['impact']}")

    if mitigations:
        print(f"\n  💡 缓解方案:")
        for i, m in enumerate(mitigations, 1):
            print(f"    {i}. {m}")

    # ── 最终建议 ──
    print("\n" + "=" * 60)
    print("🎯 最终建议")
    print("=" * 60)

    if certifi_ok:
        print("  ✅ 推荐: 使用 certifi CA bundle 替代 verify=False")
        print("     import certifi")
        print("     requests.post(url, verify=certifi.where())")
        final_action = "use_certifi"
    elif verify_true_ok:
        print("  ✅ 推荐: 直接使用 verify=True（默认行为）")
        print("     移除 ifind_call.py 中的 verify=False 即可")
        final_action = "use_verify_true"
    else:
        print("  ⚠️ verify=True 和 certifi 均失败")
        print("  推荐方案: 手动导出 iFind 服务器证书并配置固定验证")
        print("    1. openssl s_client -connect api-mcp.51ifind.com:8643 </dev/null \\")
        print("       | sed -ne '/-BEGIN CERTIFICATE-/,/-END CERTIFICATE-/p' > ifind.pem")
        print("    2. requests.post(url, verify='ifind.pem')")
        final_action = "manual_cert_pin"

    # ── 保存 ──
    output_path = OUTPUT_DIR / f"ssl_probe_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump({
            "findings": findings,
            "risks": risks,
            "mitigations": mitigations,
            "recommendation": final_action,
        }, f, ensure_ascii=False, indent=2, default=str)
    print(f"\n💾 结果已保存: {output_path}")

    # ── 判定 ──
    high_risks = [r for r in risks if r["severity"] == "高"]
    if not high_risks:
        print(f"\n✅ 实验 11 通过！无高危 SSL 风险")
    else:
        print(f"\n⚠️ 实验 11 发现 {len(high_risks)} 个高危 SSL 风险，已记录缓解方案")

    return 0


if __name__ == "__main__":
    sys.exit(main())
