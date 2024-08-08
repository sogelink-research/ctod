var module, pane, terrainFolder, layerFolder, materialFolder;

var minZoomValue = 1;
var maxZoomValue = 18;
var meshingMethodValue = "grid";
var cogValue =
  "./ctod/files/test_cog.tif";
var resamplingValue = "none";
var skipCacheValue = false;
var noDataValue = 0;

document.addEventListener("DOMContentLoaded", async () => {
  try {
    module = await import(
      "https://cdn.jsdelivr.net/npm/tweakpane@4.0.1/dist/tweakpane.min.js"
    );
    setupTweakpane();
    loadCesium();
  } catch (error) {
    console.error("Error loading tweakpane:", error);
  }
});

function setupTweakpane() {
  minZoomValue = getIntParameterValue("minZoom", minZoomValue);
  maxZoomValue = getIntParameterValue("maxZoom", maxZoomValue);
  noDataValue = getIntParameterValue("noData", noDataValue);
  cogValue = getStringParameterValue("cog", cogValue);
  resamplingValue = getStringParameterValue("resamplingMethod", resamplingValue);  
  skipCacheValue = getBoolParameterValue("skipCache", skipCacheValue);
  meshingMethodValue = getStringParameterValue("meshingMethod", meshingMethodValue);

  pane = new module.Pane({
    title: "CTOD",
  });

  const CacheOptions = {
    skipCache: skipCacheValue
  };  

  skipCache = pane.addBinding(
    CacheOptions,
    "skipCache"
  );

  skipCache.on("change", (ev) => {
    skipCacheValue = ev.value;
    updateTerrainProvider();
  });

  terrainFolder = pane.addFolder({
    title: "Terrain",
  });

  layerFolder = pane.addFolder({
    title: "Layer",
  });

  materialFolder = pane.addFolder({
    title: "Shading",
    expanded: false,
  });

  createTerrainPane();
  createLayerPane();
  createMaterialPane();
}

function createMaterialPane() {
  hillshadingEnabled = materialFolder.addBinding(
    HillshadingOptions,
    "enabled"
  );
  hillshadingEnabled.on("change", (ev) => {
    if (!ev.value) {
      disableShading();
    } else {
      setShading();
    }
  });

  for (var i = 0; i < Object.keys(SlopeRampParams).length; i++) {
    const binding = materialFolder.addBinding(
      SlopeRampParams,
      Object.keys(SlopeRampParams)[i]
    );
    binding.on("change", (ev) => {
      setShading();
    });
  }

  for (var i = 0; i < Object.keys(SlopeRampColorParams).length; i++) {
    const binding = materialFolder.addBinding(
      SlopeRampColorParams,
      Object.keys(SlopeRampColorParams)[i]
    );
    binding.on("change", (ev) => {
      setShading();
    });
  }
}

function createTerrainPane() {
  const PARAMS = {
    cog: cogValue,
    resampling: resamplingValue,
    meshing: meshingMethodValue
  };

  cog = terrainFolder.addBinding(PARAMS, "cog", {});
  cog.on("change", (ev) => {
    cogValue = ev.value;
    updateTerrainProvider();
  });

  minZoom = terrainFolder.addBlade({
    view: "slider",
    label: "minZoom",
    min: 0,
    max: 16,
    value: minZoomValue,
    format: (e) => Math.round(e),
  });

  minZoom.on("change", (ev) => {
    zoom = Math.round(ev.value);
    if (minZoomValue === zoom) {
      return;
    }

    minZoomValue = zoom;
    updateTerrainProvider();
  });

  maxZoom = terrainFolder.addBlade({
    view: "slider",
    label: "maxZoom",
    min: 17,
    max: 23,
    value: maxZoomValue,
    format: (e) => Math.round(e),
  });

  maxZoom.on("change", (ev) => {
    zoom = Math.round(ev.value);
    if (maxZoomValue === zoom) {
      return;
    }

    maxZoomValue = zoom;
    updateTerrainProvider();
  });

  noData = terrainFolder.addBlade({
    view: "slider",
    label: "noData",
    min: -100,
    max: 100,
    value: noDataValue,
    format: (e) => Math.round(e),
  });

  noData.on("change", (ev) => {
    nod = Math.round(ev.value);
    if (noDataValue === nod) {
      return;
    }

    noDataValue = nod;
    updateTerrainProvider();
  });

  const resamplingMethod = terrainFolder.addBinding(PARAMS, "resampling", {
    options: {
      none: "none",
      nearest: "nearest",
      bilinear: "bilinear",
      cubic: "cubic",
      cubic_spline: "cubic_spline",
      lanczos: "lanczos",
      average: "average",
      mode: "mode",
      gauss: "gauss",
      rms: "rms",
    },
  });

  resamplingMethod.on("change", (ev) => {
    resamplingValue = ev.value;
    updateTerrainProvider();
  });

  const meshingMethod = terrainFolder.addBinding(PARAMS, "meshing", {
    options: {
      grid: "grid",
      delatin: "delatin",
      martini: "martini"
    },
  });

  meshingMethod.on("change", (ev) => {
    meshingMethodValue = ev.value;
    updateTerrainProvider();
  });
}

function createLayerPane() {
  const PARAMS = {
    layer: "Streets",
    wireframe: false,
    grid: false,
    coords: false,
  };

  const layer = layerFolder.addBinding(PARAMS, "layer", {
    options: {
      Streets: "Streets",
      Satellite: "Satellite",
      Off: "Off",
    },
  });

  layer.on("change", (ev) => {
    handleLayerChange(ev.value);
  });

  const grid = layerFolder.addBinding(PARAMS, "grid");
  grid.on("change", (ev) => {
    useGridProvider(ev.value);
  });

  const tileCoordinates = layerFolder.addBinding(PARAMS, "coords");
  tileCoordinates.on("change", (ev) => {
    useCoordinatesProvider(ev.value);
  });

  const wireframe = layerFolder.addBinding(PARAMS, "wireframe");
  wireframe.on("change", (ev) => {
    setWireframe(ev.value);
  });
}

function updateTerrainProvider() {
  setTerrainProvider(minZoomValue, maxZoomValue, noDataValue, cogValue, resamplingValue, skipCacheValue, meshingMethodValue);
}

function getStringParameterValue(param, defaultValue) {
  return getUrlParamIgnoreCase(param) || defaultValue;
}

function getIntParameterValue(param, defaultValue) {
  return getUrlParamIgnoreCase(param) ? parseInt(getUrlParamIgnoreCase(param)) : defaultValue;
}

function getBoolParameterValue(param, defaultValue) {
  return getUrlParamIgnoreCase(param) ? getUrlParamIgnoreCase(param).toLowerCase() === "true" ? true : false : defaultValue;
}
