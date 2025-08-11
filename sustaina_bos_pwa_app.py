"""
SustainaBOS — PWA-ready Flask app (single-file)

This file is a mobile-friendly upgrade of your existing app.py.
It adds PWA support (manifest + service-worker), responsive layout, and a few small UX
improvements to make the site behave like a smartphone app (Add to Home Screen).

How to use
1. Replace your existing app.py with this file (or merge features you need).
2. Put your Excel file and static assets (icons used below) into the /static folder.
3. Run locally: python SustainaBOS_PWA_app.py
4. Deploy to Render as you currently do (render will serve the same Flask app).

Notes & next steps
- This is a Progressive Web App (PWA). It's the fastest way to have an "app" on phones
  without building separate native binaries.
- If you want a native app (APK / IPA), the PWA can be wrapped in a WebView (e.g. with
  Capacitor or Cordova) or used via Trusted Web Activity (Android).
- For secure Excel on SharePoint, you'll need an authenticated backend to fetch the file;
  right now the code reads a local Excel file as in your original app.py.

"""

from flask import Flask, render_template_string, request, jsonify, send_from_directory, Response, url_for
import pandas as pd
import matplotlib.pyplot as plt
import os

app = Flask(__name__)

# === Path to your Excel file (same as original) ===
FILE_PATH = 'Vessel_Device_Installation_Tracker NV.xlsx'

# --- Minimal safe reads: if file missing, create empty dataframes ---
if os.path.exists(FILE_PATH):
    df = pd.read_excel(FILE_PATH, engine='openpyxl', names=['Vessel Name/ ID','Spec','Devices','Installation Status','Date of Installation','Savings/year (fuel efficiency)','Savings/year (Maitenance)','Co2 savings ton/year'], skiprows=7, usecols="B:I")
    list_df = pd.read_excel(FILE_PATH, engine='openpyxl', sheet_name='Tracker', skiprows=6, nrows=418, usecols="B:J")
    summary_df = pd.read_excel(FILE_PATH, engine='openpyxl', sheet_name='Summary', skiprows=0,  nrows=13, usecols="A:F")
    summary2_df = pd.read_excel(FILE_PATH, engine='openpyxl', sheet_name='Summary', skiprows=15,  nrows=3, usecols="B:C")
    summary3_df = pd.read_excel(FILE_PATH, engine='openpyxl', sheet_name='Summary', skiprows=0,  nrows=4, usecols="I:K")
    listvessel_df = pd.read_excel(FILE_PATH, engine='openpyxl', sheet_name='Summary', skiprows=21,  nrows=70, usecols="A")
    listdevice_df = pd.read_excel(FILE_PATH, engine='openpyxl', sheet_name='Summary', skiprows=1,  nrows=12, usecols="A")
else:
    df = pd.DataFrame()
    list_df = pd.DataFrame()
    summary_df = pd.DataFrame()
    summary2_df = pd.DataFrame()
    summary3_df = pd.DataFrame()
    listvessel_df = pd.DataFrame({"Vessel": []})
    listdevice_df = pd.DataFrame({"Device": []})

# --- Utility functions copied from your original app (kept simple) ---

def get_vessel_summary(vessel_name):
    if list_df.empty:
        return None
    start_idx = list_df[list_df.iloc[:, 1] == vessel_name].index
    if len(start_idx) == 0:
        return None
    start = start_idx[0]
    end = start + 1
    while end < len(list_df) and pd.isna(list_df.iloc[end, 0]):
        end += 1
    summaryBIS_df = list_df.iloc[start:end].copy()
    return summaryBIS_df

@app.route('/get_vessel_summary', methods=['POST'])
def get_vessel_summary_route():
    vessel_name = request.json.get('vesselName')
    summaryBIS_df = get_vessel_summary(vessel_name)
    if summaryBIS_df is None:
        return jsonify({'error': 'Vessel not found or data not loaded.'}), 404
    summaryBIS_df = summaryBIS_df.fillna('')
    column_names2 = [
        'N','Vessel Name/ ID','Spec','Devices','Installation Status','Date of Installation','Savings/year (fuel efficiency)','Savings/year (Maitenance)','Co2 savings ton/year'
    ]
    summaryBIS_df.columns = column_names2
    return summaryBIS_df.to_html(index=False, classes='table table-bordered table-striped', border=0)


def get_device_summary(device_name):
    if list_df.empty:
        return pd.DataFrame()
    filtered_df = list_df[(list_df.iloc[:, 3] == device_name) & (list_df.iloc[:, 4].isin(["Done", "In Process"]))].copy()
    vessel_names = []
    for idx in filtered_df.index:
        vessel_name = None
        search_idx = idx
        while search_idx >= 0:
            val = list_df.iloc[search_idx, 1]
            if pd.notna(val):
                vessel_name = val
                break
            search_idx -= 1
        vessel_names.append(vessel_name)
    filtered_df.insert(0, "Vessel Name", vessel_names)
    cols = ["Vessel Name"] + list(filtered_df.columns[4:10])
    return filtered_df[cols]

@app.route('/get_device_summary', methods=['POST'])
def get_device_summary_route():
    device_name = request.json.get('deviceName')
    filtered_df = get_device_summary(device_name)
    if filtered_df.empty:
        return jsonify({'error': 'No data or device not found.'}), 404
    filtered_df = filtered_df.fillna('').infer_objects(copy=False)
    column_names3 = [
        'Vessel Name','Devices','Installation Status','Date of Installation','Savings/year (fuel efficiency)','Savings/year (Maitenance)','Co2 savings ton/year'
    ]
    filtered_df.columns = column_names3
    return filtered_df.to_html(index=False, classes='table table-bordered table-striped', border=0)

# Generate a simple top vessels chart if data exists
if not df.empty:
    try:
        vessels_of_interest = df[df['Vessel Name/ ID'].astype(str).str.contains('Britoil|ENA Habitat|BOS|Lewek Hydra|Nautical Aisia|Nautical Anisha|Paragon Sentinel', na=False)]
        vessel_devices = vessels_of_interest[['Vessel Name/ ID', 'Devices', 'Installation Status', 'Savings/year (fuel efficiency)', 'Savings/year (Maitenance)', 'Co2 savings ton/year']]
        vessel_devices['Savings/year (fuel efficiency)'] = pd.to_numeric(vessel_devices['Savings/year (fuel efficiency)'], errors='coerce')
        vessel_devices['Savings/year (Maitenance)'] = pd.to_numeric(vessel_devices['Savings/year (Maitenance)'], errors='coerce')
        vessel_devices['Co2 savings ton/year'] = pd.to_numeric(vessel_devices['Co2 savings ton/year'], errors='coerce')
        vessel_devices['Total Savings'] = vessel_devices['Savings/year (fuel efficiency)'].fillna(0) + vessel_devices['Savings/year (Maitenance)'].fillna(0) + vessel_devices['Co2 savings ton/year'].fillna(0)
        top_vessels = vessel_devices.groupby('Vessel Name/ ID')['Total Savings'].sum().nlargest(10).reset_index()
        plt.figure(figsize=(10, 6))
        plt.bar(top_vessels['Vessel Name/ ID'], top_vessels['Total Savings'])
        plt.xticks(rotation=45)
        plt.tight_layout()
        os.makedirs('static', exist_ok=True)
        plt.savefig('static/top_vessels_chart.png')
        plt.close()
    except Exception as e:
        print('Could not create chart:', e)

# === PWA assets served by Flask ===
@app.route('/manifest.json')
def manifest():
    manifest_data = {
        "name": "SustainaBOS",
        "short_name": "SustainaBOS",
        "start_url": "/",
        "display": "standalone",
        "background_color": "#ffffff",
        "theme_color": "#4caf50",
        "icons": [
            {"src": url_for('static', filename='icons/icon-192.png'), "sizes": "192x192", "type": "image/png"},
            {"src": url_for('static', filename='icons/icon-512.png'), "sizes": "512x512", "type": "image/png"}
        ]
    }
    return jsonify(manifest_data)

@app.route('/service-worker.js')
def service_worker():
    js = """
    const CACHE_NAME = 'sustainabos-cache-v1';
    const OFFLINE_URL = '/';
    self.addEventListener('install', (event) => {
      event.waitUntil(
        caches.open(CACHE_NAME).then((cache) => cache.addAll([OFFLINE_URL]))
      );
    });
    self.addEventListener('fetch', (event) => {
      event.respondWith(
        caches.match(event.request).then((response) => response || fetch(event.request))
      );
    });
    """
    return Response(js, mimetype='application/javascript')

# === Main responsive HTML (keeps most of your original layout but adds mobile-friendly meta & styles) ===
HTML = r"""
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no">
  <meta name="theme-color" content="#4caf50">
  <link rel="manifest" href="/manifest.json">
  <title>SustainaBOS</title>
  <style>
    /* Mobile-first styles */
    :root { --primary: #4caf50; --accent: purple; }
    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Arial; margin:0; background:#f6fbf6; color:#222; }
    header { background: #D0E8D0; padding:12px; display:flex; align-items:center; gap:12px; }
    header img { height:36px; }
    header h1 { font-size:18px; margin:0; }
    nav { margin-left:auto; }
    nav a { margin-left:12px; color:var(--accent); text-decoration:none; font-weight:600; }
    .container { padding:12px; max-width:1100px; margin:0 auto; }
    .section { background:white; border-radius:10px; padding:12px; margin-bottom:12px; box-shadow:0 2px 6px rgba(0,0,0,0.06); }
    button { background:var(--primary); color:white; border:none; padding:12px; border-radius:8px; font-weight:700; width:100%; margin-bottom:8px; }
    .row { display:flex; gap:12px; flex-direction:column; }
    @media(min-width:900px){ .row { flex-direction:row; } button{ width:auto; } }
    table { width:100%; border-collapse: collapse; }
    th,td{ padding:8px; border:1px solid #eee; text-align:left; }
    iframe { width:100%; border:0; }
    #fab-button{ position:fixed; right:16px; bottom:16px; width:60px; height:60px; border-radius:30px; background:white; display:flex; align-items:center; justify-content:center; box-shadow:0 8px 20px rgba(0,0,0,0.12); }
  </style>
</head>
<body>
  <header>
    <img src="/static/green_leaf.png" alt="logo">
    <h1>SustainaBOS</h1>
    <nav>
      <a href="#" onclick="show('home')">Home</a>
      <a href="#" onclick="show('list')">List</a>
      <a href="#" onclick="show('analytics')">Analytics</a>
      <a href="#" onclick="show('report')">Report</a>
      <a href="#" onclick="show('contact')">Contact</a>
    </nav>
  </header>
  <div class="container">
    <div id="home" class="section">
      <h2>Welcome</h2>
      <p>Open the PWA menu (Add to Home Screen) to install this tool on your phone.</p>
      <div style="margin-top:8px;">
        <iframe height="160" src="https://app.powerbi.com/reportEmbed?reportId=1062d591-1686-420c-bd67-580dcef8cd4c&autoAuth=true&ctid=0bb4d87c-b9a5-49c3-8a59-4347acef01d8&navContentPaneEnabled=false&filterPaneEnabled=false"></iframe>
      </div>
    </div>

    <div id="list" class="section" style="display:none;">
      <h2>List</h2>
      <div class="row">
        <button onclick="showVesselSelector()">Show One Vessel</button>
        <button onclick="showDeviceSelector()">Show One Device</button>
      </div>

      <div id="vesselSelector" style="display:none; margin-top:8px;">
        <label>Which vessel?</label>
        <select id="vesselDropdown" style="width:100%; padding:8px; margin-top:6px;">
          {% for vessel in listvessel_df['BOS DUBAI'] %}
            <option value="{{ vessel }}">{{ vessel }}</option>
          {% endfor %}
        </select>
        <button onclick="confirmVesselSelection()" style="margin-top:8px;">Ok</button>
      </div>

      <div id="deviceSelector" style="display:none; margin-top:8px;">
        <label>Which device?</label>
        <select id="deviceDropdown" style="width:100%; padding:8px; margin-top:6px;">
          {% for device in listdevice_df['Device'] %}
            <option value="{{ device }}">{{ device }}</option>
          {% endfor %}
        </select>
        <button onclick="confirmDeviceSelection()" style="margin-top:8px;">Ok</button>
      </div>

      <div id="vesselSummaryDisplay" style="margin-top:10px;"></div>
      <div id="deviceSummaryDisplay" style="margin-top:10px;"></div>
    </div>

    <div id="analytics" class="section" style="display:none;">
      <h2>Analytics</h2>
      <div id="analyticsContainer"></div>
    </div>

    <div id="report" class="section" style="display:none;">
      <h2>Reports</h2>
      <iframe height="420" src="/static/Report2024.pdf"></iframe>
    </div>

    <div id="contact" class="section" style="display:none;">
      <h2>Contact</h2>
      <p>Axel Faurax</p>
      <p>axel.faurax@britoil.com.sg</p>
    </div>

  </div>

  <a id="fab-button" href="#" title="Refresh" onclick="location.reload(); return false;">
    <img src="/static/green_leaf.png" alt="fab" style="height:32px;">
  </a>

  <script>
    // Basic client-side navigation
    function show(id){
      ['home','list','analytics','report','contact'].forEach(s=>document.getElementById(s).style.display='none');
      document.getElementById(id).style.display='block';
      if(id==='analytics'){ document.getElementById('analyticsContainer').innerHTML = '<iframe height="600" src="https://app.powerbi.com/reportEmbed?reportId=19eea1f2-00f5-4fcf-8d6d-6bed6f27d0e5&autoAuth=true&ctid=0bb4d87c-b9a5-49c3-8a59-4347acef01d8&navContentPaneEnabled=false&filterPaneEnabled=false"></iframe>'; }
    }
    show('home');

    // PWA: handle install prompt for nicer UX on mobile
    let deferredPrompt;
    window.addEventListener('beforeinstallprompt', (e) => {
      e.preventDefault();
      deferredPrompt = e;
      // Show a small install hint — for demo we'll use a console hint
      console.log('PWA install available');
    });
    function promptInstall(){
      if(deferredPrompt){
        deferredPrompt.prompt();
        deferredPrompt.userChoice.then((choiceResult)=>{ deferredPrompt = null; });
      } else { alert('Use your browser menu -> Add to Home screen'); }
    }

    // Helpers used by list UI
    function showVesselSelector(){ document.getElementById('vesselSelector').style.display='block'; }
    function showDeviceSelector(){ document.getElementById('deviceSelector').style.display='block'; }
    function confirmVesselSelection(){
      const v = document.getElementById('vesselDropdown').value;
      fetch('/get_vessel_summary', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({vesselName:v})}).then(r=>r.text()).then(html=>{ document.getElementById('vesselSummaryDisplay').innerHTML = html; }).catch(()=>alert('Error'));
    }
    function confirmDeviceSelection(){
      const d = document.getElementById('deviceDropdown').value;
      fetch('/get_device_summary', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({deviceName:d})}).then(r=>r.text()).then(html=>{ document.getElementById('deviceSummaryDisplay').innerHTML = html; }).catch(()=>alert('Error'));
    }

    // Register the service worker
    if('serviceWorker' in navigator){
      navigator.serviceWorker.register('/service-worker.js').then(()=>console.log('SW registered')).catch(()=>console.log('SW failed'));
    }
  </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML, listvessel_df=listvessel_df, listdevice_df=listdevice_df)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)
