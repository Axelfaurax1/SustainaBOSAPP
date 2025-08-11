"""
SustainaBOS — PWA-updated Flask app (keeps original UI + mobile responsive tweaks)

This file is your original app.py enhanced with:
- PWA manifest and service-worker endpoints (/manifest.json and /service-worker.js)
- meta viewport and theme-color for mobile
- responsive CSS overrides (images, iframes, tables, container widths)
- install prompt handling and service worker registration in the client
- icons saved in static/icons (icon-192.png and icon-512.png) and static/green_leaf.png

HOW TO DEPLOY
1. Rename this file to app.py in your Render repository (if Render expects app.py).
2. Ensure the Excel file "Vessel_Device_Installation_Tracker NV.xlsx" is present at the app root.
3. Ensure the folder "static/icons" contains icon-192.png and icon-512.png and that static/ contains green_leaf.png and all other images referenced by the template.
4. Keep your existing requirements.txt (flask, pandas, matplotlib, openpyxl, pillow if used locally).
5. Deploy to Render and visit the URL on your phone. Use the browser menu -> Add to Home screen (or install prompt) to make it an app.

"""

# ----- Begin original app with PWA additions -----

import pandas as pd
import matplotlib.pyplot as plt
from flask import Flask, render_template_string, request

# Create a Flask app
app = Flask(__name__)


# Load the Excel file with specified column names starting from row 8 and column B
file_path = 'Vessel_Device_Installation_Tracker NV.xlsx'
column_names = ['Vessel Name/ ID', 'Spec', 'Devices', 'Installation Status', 'Date of Installation', 'Savings/year (fuel efficiency)', 'Savings/year (Maitenance)', 'Co2 savings ton/year']
df = pd.read_excel(file_path, engine='openpyxl', names=column_names, skiprows=7, usecols="B:I")

list_df = pd.read_excel(file_path, engine='openpyxl', sheet_name='Tracker', skiprows=6, nrows=418, usecols="B:J")

# Load the summary sheet
summary_df = pd.read_excel(file_path, engine='openpyxl', sheet_name='Summary', skiprows=0,  nrows=13, usecols="A:F")
summary2_df = pd.read_excel(file_path, engine='openpyxl', sheet_name='Summary', skiprows=15,  nrows=3, usecols="B:C")
summary3_df = pd.read_excel(file_path, engine='openpyxl', sheet_name='Summary', skiprows=0,  nrows=4, usecols="I:K")
listvessel_df = pd.read_excel(file_path, engine='openpyxl', sheet_name='Summary', skiprows=21,  nrows=70, usecols="A")
listdevice_df = pd.read_excel(file_path, engine='openpyxl', sheet_name='Summary', skiprows=1,  nrows=12, usecols="A")

# Utility functions

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
    vessel_name = request.json.get('vesselName') if request.json else request.form.get('vesselName')
    summaryBIS_df = get_vessel_summary(vessel_name)
    if summaryBIS_df is None:
        return {'error': 'Vessel not found or data not loaded.'}, 404
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
    device_name = request.json.get('deviceName') if request.json else request.form.get('deviceName')
    filtered_df = get_device_summary(device_name)
    if filtered_df.empty:
        return {'error': 'No data or device not found.'}, 404
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

# ---- HTML template (original UI preserved) ----
html_template = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no">
  <link rel="manifest" href="/manifest.json">
  <meta name="theme-color" content="#4caf50">
  <link rel="icon" href="{{ url_for('static', filename='favicon.ico') }}" type="image/x-icon">
    <style>
/* Responsive overrides for mobile */
:root{ --primary:#4caf50; }
@media(max-width:900px){ .container{width:95%;} header nav{display:none;} header #branding img{height:48px;} img{max-width:100%;height:auto;} iframe{max-width:100%;height:auto;} table{font-size:12px;} #splash-logo{height:64px;} }
        body { font-family: Arial, sans-serif; background-color: #E8F5E9; margin: 0; padding: 0; }
        .container { width: 80%; margin: auto; overflow: hidden; }
        header { background: #D0E8D0; color: #800080; padding-top: 20px; min-height: auto; border-bottom: #800080 2px solid; }
        header a { color: #800080; text-decoration: none; text-transform: none; font-size: 16px; font-weight: bold;}
        header ul { padding: 0; list-style: none; }
        header li { display: inline; padding: 0 10px 0 20px; }
        header #branding { float: left; }
        header #branding h1 { font-size: 19px; }
        header nav { float: right; margin-top: 10px; }
        .menu a { margin-right: 20px; text-decoration: none; color: #800080; font-weight: bold; }
        .menu a:hover { color: #0779e4; }
        .content { padding: 20px; background-color: #fff; border-radius: 5px; margin-top: 20px; }
        table {
        width: 100%; border-collapse: collapse; margin-bottom: 20px; box-shadow: 0 2px 3px rgba(0,0,0,0.1);
        }
        th, td {
        border: 1px solid #ddd;
        padding: 12px;
        text-align: left;
        }
        th { background-color: #0779e4; color: white; }
        h2 { color: #333; }
        .hidden { display: none; }
        .show { display: table-row-group; }
        .report-section ul li a:hover {
            text-decoration: underline;
            color: #0056b3;
         }
         /* additional original styles retained */
    </style>
    <script>
        function toggleVisibility(id) {
            var element = document.getElementById(id);
            if (element.classList.contains('hidden')) {
                element.classList.remove('hidden');
                element.classList.add('show');
            } else {
                element.classList.remove('show');
                element.classList.add('hidden');
            }
        }

        function loadPowerBIReport() {
           document.getElementById("analyticsContainer").innerHTML = `
           <iframe title="SustainaBOS7" width="950" height="1250"
        src="https://app.powerbi.com/reportEmbed?reportId=19eea1f2-00f5-4fcf-8d6d-6bed6f27d0e5&autoAuth=true&ctid=0bb4d87c-b9a5-49c3-8a59-4347acef01d8&navContentPaneEnabled=false&filterPaneEnabled=false"
           frameborder="0" allowFullScreen="true">
           </iframe>
    `      ;
        }

        function showSection(sectionId) {
            // hide all
            var sections = ['welcome', 'list', 'analytics', 'report', 'contact'];
            sections.forEach(function(s) { document.getElementById(s).classList.add('hidden'); });
            // show the requested
            document.getElementById(sectionId).classList.remove('hidden');
            // load analytics lazily
            if (sectionId === 'analytics') {
                loadPowerBIReport();
            }
        }

        // Misc helpers preserved from original app
        var currentAction = null;

        function modifyStatus() {
        console.log("Modify Status button clicked");
        currentAction = "modifyStatus"; // Store the action type
        showVesselSelector();
        }

        function showVessel() {
        console.log("Show Vessel button clicked");
        currentAction = "showVessel"; // Store the action type
        showVesselSelector();
        }

        function showDevice() {
        console.log("Show Device button clicked");
        currentAction = "showDevice"; // Store the action type
        showDeviceSelector();
        }

        function showVesselSelector() {
        const vesselSelector = document.getElementById('vesselSelector');
        vesselSelector.style.display = 'block';
        }

        function showDeviceSelector() {
        const deviceSelector = document.getElementById('deviceSelector');
        deviceSelector.style.display = 'block';
        }

        function confirmVesselSelection(){
            const v = document.getElementById('vesselDropdown').value;
            fetch('/get_vessel_summary', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({vesselName:v})}).then(r=>r.text()).then(html=>{ document.getElementById('vesselSummaryDisplay').innerHTML = html; }).catch(()=>alert('Error'));
        }

        function confirmDeviceSelection(){
            const d = document.getElementById('deviceDropdown').value;
            fetch('/get_device_summary', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({deviceName:d})}).then(r=>r.text()).then(html=>{ document.getElementById('deviceSummaryDisplay').innerHTML = html; }).catch(()=>alert('Error'));
        }

    </script>
</head>
<body>

    <div id="splash">
    <img src="{{ url_for('static', filename='green_leaf.png') }}" alt="Logo" id="splash-logo">
    <div id="splash-title">
        <span class="green">Sustaina</span><span class="purple">BOS</span>
    </div>
    </div>

    <a href="javascript:void(0);" id="fab-button" title="Reload Page">
    <img src="{{ url_for('static', filename='green_leaf.png') }}" alt="FAB Logo">
    </a>

    <header>
      <div class="container">
        <div id="branding">
          <img src="{{ url_for('static', filename='britoil_logo.png') }}" alt="Britoil Offshore Services Logo" style="height:38px;">
          
          <h1>Fleet Sustainability View</h1>
          <br>
        </div>
        <nav>
          <ul>
            <li><a id="nav-welcome" href="#" onclick="showSection('welcome')">Home</a></li>
            <li><a id="nav-list" href="#" onclick="showSection('list')">List</a></li>
            <li><a id="nav-analytics" href="#" onclick="showSection('analytics')">Analytics</a></li>
            <li><a id="nav-report" href="#" onclick="showSection('report')">Report</a></li>
            <li><a id="nav-contact" href="#" onclick="showSection('contact')">Contact</a></li>
          </ul>
        </nav>
      </div>
    </header>

    <div class="container">

      <div id="welcome" class="section content">
          <h2>Welcome</h2>
          <p>This is the Fleet Sustainability View powered by the Sustainabos tool.</p>

          <h3>Scope 1, 2, 3 - Reminder :</h3>
          <p> Here is both an explanation and a reminder of what these scopes are...</p>

          <img src="{{ url_for('static', filename='Scopes.png') }}" alt="Scopes" style="width:950px; display: block; margin: auto;">

          <br>
          <h3>Green News :</h3>
          <p> <b> BOS Princess: Successfully Converted Into Geotechnical Drilling Vessel </b> 🛠 <br> <br>

          We are pleased to announce the successful conversion of BOS Princess into a geotechnical drilling vessel, increasing our capabilities in support of the offshore wind industry.
          <br> <br>
          As part of this transformation, Besiktas Shipyard carried significant upgrades to the structure and systems to ensure optimal performance in demanding offshore conditions.
          <br> <br>
          With these upgrades, BOS Princess will provide a stable and efficient platform for geotechnical operations, strengthening our commitment to advancing offshore wind energy. </p>
          <br> <br>
          <img src="{{ url_for('static', filename='Princess.jpeg') }}" alt="Princess" style="height:600px; display: block; margin: auto;">

      <br>

      <h2><span class="green">Sustaina</span><span class="purple">BOS</span> </h2>
      Powered by Axel FAURAX and Technical Department.

      <br>
      <br>
          <img src="{{ url_for('static', filename='view2.png') }}"  alt="ESG" style="height:400px; display: block; margin: auto;">

      </div>

      <div id="list" class="section content hidden">

          <h2>List</h2>
          <div style="display:flex; gap: 10px; flex-wrap:wrap;">
             <button onclick="showVessel()">Show Vessel</button>
             <button onclick="showDevice()">Show Device</button>
             <button onclick="modifyStatus()">Modify Status</button>
          </div>

          <div id="vesselSelector" style="display:none; margin-top: 8px;">
            <label>Which vessel?</label>
            <select id="vesselDropdown" style="width:100%; padding:8px; margin-top:6px;">
              {% for vessel in listvessel_df['A'] %}
                <option value="{{ vessel }}">{{ vessel }}</option>
              {% endfor %}
            </select>
            <button onclick="confirmVesselSelection()" style="margin-top:8px;">Ok</button>
          </div>

          <div id="deviceSelector" style="display:none; margin-top: 8px;">
            <label>Which device?</label>
            <select id="deviceDropdown" style="width:100%; padding:8px; margin-top:6px;">
              {% for device in listdevice_df['Device'] %}
                <option value="{{ device }}">{{ device }}</option>
              {% endfor %}
            </select>
            <button onclick="confirmDeviceSelection()" style="margin-top:8px;">Ok</button>
          </div>

          <!--  This is where the summary table will appear -->
          <div id="vesselSummaryDisplay" style="margin-top: 20px;"></div>
          <div id="deviceSummaryDisplay" style="margin-top: 20px;"></div>

          <br>

          <h3>New Initiatives - Look</h3>
          <img src="{{ url_for('static', filename='initiatives1.png') }}"  alt="ini" style="height:300px; display: block; margin: auto;">

          <h3>Summary Track Sheet</h3>
          <table>
              {% for index, row in summary_df.iterrows() %}
              <tr>
                  {% for i, value in row.items() %}
                  {% if index == 0 %}
                  <td style="font-weight: bold;">{{ value }}</td>
                  {% elif loop.last %}
                  <td>
                     {% if value is number %}
                     <span style="color: {% if value >= 0.505 %}green{% elif value > 0.305 %}orange{% else %}red{% endif %}; font-weight: bold;"> 
                        {{ (value * 100) | round(0) }}%
                     </span>
                     {% else %}
                     {{ value }}
                     {% endif %}
                  </td>
                  {% else %}
                  <td>{{ value }}</td>
                  {% endif %}
                  {% endfor %}
              </tr>
              {% endfor %}
          </table>
          {% endfor %}
      </div>

      <div id="analytics" class="section content hidden">
          <h2>Analytics</h2>

          <p> You can interact with BI charts after sign in. Refresh if any issues </p>

          <h3>BI Analysis</h3>

          <div id="analyticsContainer"></div>

          <h3>Old Analytics</h3>
          <table>
              {% for index, row in summary3_df.iterrows() %}
              <tr>
                  {% for col_index in range(row.size) %}
                  <td>{{ row.iloc[col_index] }}</td>
                  {% endfor %}
              </tr>
              {% endfor %}
          </table>

          <h3>Top Devices - CO2 saving</h3>
          <div style="display:flex; justify-content:center; gap:20px; flex-wrap:wrap;">
             <img src="{{ url_for('static', filename='top_devices_chart.png') }}" alt="CO2 Savings by Devices" width="450">
             <img src="{{ url_for('static', filename='top_vessels_chart.png') }}" alt="Top Vessels - Savings" width="450">
          </div>

          <h3>Track progress bars</h3>
          <div style="display: flex; justify-content: center; gap: 20px;">
             <img src="{{ url_for('static', filename='track_chartEX.png') }}" alt="Track" width="450">
             <img src="{{ url_for('static', filename='track_chartEX2.png') }}" alt="Track" width="450">

          </div>
          <br>

          <h3>Overdue Jobs - Statistics for PMS</h3>
          <p> Besides Sustainability, I'm also doing statistics and analysis on PMS overdue tasks — this helps maintenance planning and budgeting.</p> <br><br>
          <div style="display: flex; justify-content: center; gap: 20px;">
             <img src="{{ url_for('static', filename='OJ_worstEX.png') }}" alt="Track" width="450">
             <img src="{{ url_for('static', filename='OJ_worstEX2.png') }}" alt="Track" width="450">

          </div>



      </div>

      <div id="report" class="section content hidden">
         <h2>All Documents</h2>
         <br>
         <h3>Sustainability Report 2024</h3>
         Here is the sustainabilty report of 2024. I hope this helps for the 2025 report. Or help to do it. Here is the PDF display. <br> <br> 
         <iframe src="{{ url_for('static', filename='Report2024.pdf') }}" width="100%" height="600px">
         </iframe>

         <div class="report-section" style="margin-top: 30px;">
           <h3>📄 Presentations</h3>
             <ul style="list-style-type: none; padding-left: 20; margin:0;">
               <li style="margin-bottom: 12px;"><a href="https://..." target="_blank">🔗 IWTM Filters Study</a></li>
               <li style="margin-bottom: 12px;"><a href="https://..." target="_blank">🔗 New Initiatives Presentation – Dubai 2024</a></li>
               <li style="margin-bottom: 12px;"><a href="https://..." target="_blank">🔗 New Initiatives 2025</a></li>
             </ul>
         </div>

         <div class="report-section" style="margin-top: 30px;">
           <h3>📄 DataBases and Excel Calculators</h3>
             <ul style="list-style-type: none; padding-left: 20; margin:0;">
               <li style="margin-bottom: 12px;"><a href="https://..." target="_blank">🔗 Vessel Device Installation Tracker NV </a></li>
               <li style="margin-bottom: 12px;"><a href="https://..." target="_blank">🔗 PMS Overdue and Postponed Stats</a></li>
               <li style="margin-bottom: 12px;"><a href="https://..." target="_blank">🔗 LED Calculator Fuel Savings</a></li>
               <li style="margin-bottom: 12px;"><a href="https://..." target="_blank">🔗 Digital Ocean Status - ERP Initiative</a></li>
               <li style="margin-bottom: 12px;"><a href="https://..." target="_blank">🔗 Britoil Technical Plan 2025 Updated</a></li>

               <li style="margin-bottom: 12px;"><a href="https://..." target="_blank">🔗 IWTM Samples Data & Analysis Britoil 121 (ex)</a></li>
             </ul>
         </div>
      </div>

      <div id="contact" class="section content hidden">

          <div id="instruction-box-nul" style="display: none; position: fixed; bottom: 20px; right: 20px; background: #fff; padding: 16px; border-radius: 8px; box-shadow: 0 5px 15px rgba(0,0,0,0.1); z-index: 9999; transition: opacity 1s ease; opacity: 0;">
              <strong>HELLO ! </strong><br><br>
              <b>Feel free to contact me ^^</b>
          </div>

          <h2>Contact</h2>
          <p>Name: Axel Faurax</p>
          <p>Phone (SG): +65 81298204 </p>
          <p>Phone (FR): +33 771770134 </p>

          <button onclick="promptInstall()">Install app on this device</button>

      </div>

    </div>

    <footer style="background: #2d2d2d; color: #fff; padding: 20px; margin-top: 30px;">
       <div class="container" style="text-align: center;">
         <p style="margin: 5px 0;">&copy; 2025 Britoil Offshore Services. All rights reserved.</p>
         <p style="margin: 5px 0;">
              <a href="mailto:info@britoil.com" style="color: #ccc; text-decoration: none;">Contact us</a> |
              <a href="/privacy-policy" style="color: #ccc; text-decoration: none;">Privacy Policy</a> |
              <a href="/terms-of-service" style="color: #ccc; text-decoration: none;">Terms of Service</a>
         </p>
       </div>
    </footer>

   <!-- JavaScript for splash animation -->
   <script>
      setTimeout(function () {
         document.getElementById('splash').style.display = 'none';
      }, 2500);
      document.getElementById("fab-button").addEventListener("click", function() {
            location.reload();
      });
      // Initialize showing welcome section
      window.onload = function() {
            showSection('welcome');

      };
   </script>

    <script>
    // PWA install prompt handling
    let deferredPrompt;
    window.addEventListener('beforeinstallprompt', (e) => {
      e.preventDefault();
      deferredPrompt = e;
      // show a subtle hint on mobile (console for now)
      console.log('PWA install available');
    });
    function promptInstall(){ if(deferredPrompt){ deferredPrompt.prompt(); deferredPrompt.userChoice.then(()=>{ deferredPrompt = null; }); } else { alert('Use browser menu -> Add to Home screen'); } }
    // register service worker
    if('serviceWorker' in navigator){ navigator.serviceWorker.register('/service-worker.js').then(()=>console.log('SW registered')).catch(()=>console.log('SW failed')); }
    </script>

</body>
</html>
"""

from flask import jsonify, Response, url_for, send_from_directory

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
    js = """const CACHE_NAME = 'sustainabos-cache-v1';
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(['/']))
  );
});
self.addEventListener('fetch', (event) => {
  event.respondWith(
    caches.match(event.request).then((response) => response || fetch(event.request))
  );
});
"""
    return Response(js, mimetype='application/javascript')


@app.route('/')
def index():
    return render_template_string(html_template, vessel_devices=df, summary_df=summary_df, summary2_df=summary2_df, summary3_df=summary3_df, listvessel_df=listvessel_df, listdevice_df=listdevice_df)

if __name__ == '__main__':
    app.run(debug=True)
