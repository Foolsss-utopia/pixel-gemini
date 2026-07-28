import requests

url = "https://raw.githubusercontent.com/proxifly/free-proxy-list/main/proxies/all/data.json"
try:
    r = requests.get(url, timeout=10)
    data = r.json()
    us_proxies = [p for p in data if p.get('geolocation', {}).get('country') in ('US', 'GB', 'CA', 'DE', 'JP')]
    print("Found eligible proxies count:", len(us_proxies))
    
    working = []
    for item in us_proxies:
        proxy_url = f"{item['protocol']}://{item['ip']}:{item['port']}"
        try:
            res = requests.get("http://ip-api.com/json", proxies={"http": proxy_url, "https": proxy_url}, timeout=3)
            if res.status_code == 200:
                print("WORKING PROXY:", proxy_url, "| Country:", res.json().get("countryCode"), "| IP:", res.json().get("query"))
                working.append(proxy_url)
                if len(working) >= 5:
                    break
        except Exception:
            pass

    if working:
        with open("proxies.txt", "w", encoding="utf-8") as f:
            f.write("\n".join(working) + "\n")
        print("Updated proxies.txt with working proxies!")
except Exception as e:
    print("Error:", str(e))
