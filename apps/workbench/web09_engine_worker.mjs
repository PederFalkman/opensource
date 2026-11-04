// WEB-09 experiment: candidate-only wheel; synthetic data; worker-isolated Python.
const RUNTIME = "https://cdn.jsdelivr.net/pyodide/v0.29.5/full/";
const PYTHON_ASSESSMENT = "import io, json, re, csv\nimport pandas as pd\nimport energydata_kit as ek\nheader = next(csv.reader(io.StringIO(csv_text), strict=True))\ncolumns = [name.strip() for name in header]\nif not columns or any(not name for name in columns) or len(set(columns)) != len(columns):\n    raise ValueError(\"Missing or duplicate CSV headers\")\nframe = pd.read_csv(io.StringIO(csv_text), dtype=str, keep_default_na=False)\nif frame.empty or list(frame.columns) != header:\n    raise ValueError(\"CSV header mismatch\")\nraw_times = frame[\"timestamp\"].astype(str).str.strip()\nif not raw_times.map(lambda s: bool(re.search(r\"(?:Z|[+-]\\d{2}:\\d{2})$\", s, re.I))).all():\n    raise ValueError(\"Timestamps need explicit UTC offset\")\ntimes = pd.to_datetime(raw_times, utc=True, format=\"ISO8601\", errors=\"raise\")\nraw_values = frame[\"power_kw\"].astype(str).str.strip()\nvalues = pd.to_numeric(raw_values.replace(\"\", float(\"nan\")), errors=\"coerce\")\nif (raw_values.ne(\"\") & values.isna()).any():\n    raise ValueError(\"Non-numeric measurement\")\nseries = pd.Series(values.to_numpy(), index=pd.DatetimeIndex(times), name=\"power_kw\")\nreport = ek.assess_quality(series, freq=\"15min\")\njson.dumps({\n    \"adapter_version\": \"energydata.workbench.python.v1\",\n    \"engine\": \"python-validated\",\n    \"package_version\": ek.__version__,\n    \"source\": \"web09-synthetic-only\",\n    \"columns\": {\"timestamp\": \"timestamp\", \"value\": \"power_kw\"},\n    \"interval_minutes\": 15,\n    \"report\": report.to_dict(),\n    \"privacy\": \"browser-worker-synthetic\"\n}, sort_keys=True, allow_nan=False)";
let interpreter = null;
let installedDigest = null;
let busy = false;

function respond(id, stage, extras = {}) {
  self.postMessage({id, stage, ...extras});
}

self.onmessage = async ({data}) => {
  if (!data || data.type !== "run-synthetic" ||
      typeof data.id !== "string" || !/^[a-z0-9-]{1,64}$/.test(data.id)) return;
  const {id} = data;
  if (busy) {respond(id,"error",{error:"Python worker already busy"});return}
  busy = true;
  try {
    if (!(data.wheelBytes instanceof ArrayBuffer) ||
        data.wheelBytes.byteLength < 1 || data.wheelBytes.byteLength > 10*1024*1024)
      throw Error("Invalid wheel bytes");
    if (typeof data.digest !== "string" || !/^[a-f0-9]{64}$/.test(data.digest))
      throw Error("Invalid SHA-256");
    if (typeof data.csvText !== "string" || data.csvText.length > 512*1024 ||
        !data.csvText.startsWith("timestamp,power_kw\r\n"))
      throw Error("Only fixed synthetic CSV is supported");
    const actual = Array.from(new Uint8Array(
      await self.crypto.subtle.digest("SHA-256", data.wheelBytes)),
      byte => byte.toString(16).padStart(2,"0")).join("");
    if (actual !== data.digest) throw Error("Wheel integrity mismatch in worker");
    respond(id,"loading",{detail:"Loading Python runtime and dependencies"});
    if (!interpreter) {
      const {loadPyodide} = await import(RUNTIME+"pyodide.mjs");
      interpreter = await loadPyodide({indexURL:RUNTIME});
      await interpreter.loadPackage(["numpy","pandas","micropip"]);
      await interpreter.runPythonAsync("import micropip\nawait micropip.install('pint==0.24.4')");
    }
    if (installedDigest === null) {
      const site = interpreter.runPython("import site\nsite.getsitepackages()[0]");
      interpreter.unpackArchive(data.wheelBytes,"wheel",{extractDir:site});
      installedDigest = actual;
    } else if (installedDigest !== actual) {
      throw Error("Different wheel requires a fresh worker");
    }
    interpreter.globals.set("csv_text",data.csvText);
    respond(id,"analyzing",{detail:"Running actual EnergyData Kit Python"});
    const result=JSON.parse(await interpreter.runPythonAsync(PYTHON_ASSESSMENT));
    if (result.report?.schema_version !== "2") throw Error("Unexpected canonical schema");
    respond(id,"complete",{result});
  } catch(error) {
    respond(id,"error",{error:String(error?.message||error)});
  } finally {busy=false}
};
