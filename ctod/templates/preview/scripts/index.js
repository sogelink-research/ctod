var viewer,
  terrainProvider,
  streetsLayer,
  satelliteLayer,
  gridLayer,
  coordinateLayer,
  currentCog,
  dataset;

function loadCesium() {
  Cesium.Ion.defaultAccessToken = undefined;

  viewer = new Cesium.Viewer("cesiumContainer", {
    imageryProvider: false,
    requestRenderMode: true,
    timeline: false,
    animation: false,
    baseLayerPicker: false,
    homeButton: false,
    navigationHelpButton: false,
    vrButton: false,
    fullscreenButton: false,
    sceneModePicker: false,
    geocoder: false,
    infoBox: false,
    msaaSamples: 1,
  });

  initializeLayers();
  initTerrainProvider();
  configureViewer();
  setShading();
}

function initializeLayers() {
  streetsLayer = new Cesium.ImageryLayer(
    new Cesium.OpenStreetMapImageryProvider({
      url: "https://tile.openstreetmap.org/",
      fileExtension: "png",
      maximumLevel: 19,
      credit: "© OpenStreetMap contributors",
    })
  );

  // Unable to find a free open satellite imagery provider
  // disabling for now
  satelliteLayer = createImageryLayerWithProvider(
    new Cesium.ArcGisMapServerImageryProvider({
      //url: "https://services.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer",
    })
  );
  gridLayer = createImageryLayerWithProvider(new Cesium.GridImageryProvider());
  coordinateLayer = createImageryLayerWithProvider(
    new Cesium.TileCoordinatesImageryProvider()
  );

  // initial state
  gridLayer.show = false;
  coordinateLayer.show = false;

  // add layers to viewer
  [streetsLayer, satelliteLayer, gridLayer, coordinateLayer].forEach(
    (layer) => {
      viewer.imageryLayers.add(layer);
    }
  );

  useStreetLayer();
}

function initTerrainProvider() {
  dataset = getUrlParamIgnoreCase("dataset") || undefined;
  const minZoom = getUrlParamIgnoreCase("minZoom") || 1;
  const maxZoom = getUrlParamIgnoreCase("maxZoom") || 18;
  const noData = getUrlParamIgnoreCase("noData") || 0;
  const cog = getUrlParamIgnoreCase("cog") || "./ctod/files/test_cog.tif";
  const skipCache = getUrlParamIgnoreCase("skipCache") || false;
  const meshingMethod = getUrlParamIgnoreCase("meshingMethod") || "grid";
  setTerrainProvider(
    minZoom,
    maxZoom,
    noData,
    cog,
    "none",
    skipCache,
    meshingMethod
  );
}

function createImageryLayerWithProvider(provider) {
  return new Cesium.ImageryLayer(provider);
}

function configureViewer() {
  viewer.scene.terrainProvider = terrainProvider;
  viewer.scene.globe.enableLighting = true;
  viewer.scene.globe.depthTestAgainstTerrain = true;
  viewer.scene.globe.baseColor = Cesium.Color.WHITE;
  viewer.clock.shouldAnimate = true;
  viewer.scene.screenSpaceCameraController.enableCollisionDetection = false;
  viewer.shadows = false;
  viewer.terrainShadows = Cesium.ShadowMode.ENABLED;
  viewer.shadowMap.maximumDistance = 1200;
  viewer.shadowMap.fadingEnabled = false;
  viewer.shadowMap.darkness = 0.65;

  // Set sun position
  const date = new Date();
  date.setUTCFullYear(2023, 7, 10);
  date.setUTCHours(13, 0, 0, 0);
  viewer.clock.currentTime = Cesium.JulianDate.fromDate(date);

  // Remove cesiums ugly click popup
  viewer.cesiumWidget.screenSpaceEventHandler.setInputAction((e) => {},
  Cesium.ScreenSpaceEventType.LEFT_CLICK);

  viewer.camera.setView({
    destination: new Cesium.Cartesian3.fromDegrees(5.33195, 60.29969, 2000),
    orientation: {
      heading: Cesium.Math.toRadians(0),
      pitch: Cesium.Math.toRadians(-80),
      roll: 0.0,
    },
  });
}

function setTerrainProvider(
  minZoom,
  maxZoom,
  noData,
  cog,
  resamplingMethod,
  skipCache,
  meshingMethod
) {
  let terrainProviderUrl = `${window.location.origin}/tiles`;

  // chosen dataset or dynamic
  if (dataset) {
    terrainProviderUrl = `${terrainProviderUrl}/${dataset}`;
  } else {
    terrainProviderUrl = `${terrainProviderUrl}/dynamic?minZoom=${minZoom}&maxZoom=${maxZoom}&noData=${noData}&cog=${cog}&skipCache=${skipCache}&meshingMethod=${meshingMethod}`;
    if (resamplingMethod !== "none") {
      terrainProviderUrl += `&resamplingMethod=${resamplingMethod}`;
    }
  }

  terrainProvider = new Cesium.CesiumTerrainProvider({
    url: terrainProviderUrl,
    requestVertexNormals: true,
  });

  viewer.terrainProvider = terrainProvider;
  if (currentCog !== cog) {
    zoomToCOG(cog, maxZoom);
  }

  currentCog = cog;
  updateViewer();
}

function zoomToCOG(cog, maxZoom) {
  let layerJsonUrl = `${window.location.origin}/tiles`;

  if (dataset) {
    layerJsonUrl = `${layerJsonUrl}/${dataset}/layer.json`;
  } else {
    layerJsonUrl = `${layerJsonUrl}/dynamic/layer.json?maxZoom=${maxZoom}&cog=${cog}`;
  }

  fetch(layerJsonUrl)
    .then((response) => response.json())
    .then((layer) => {
      console.log(layer);
      const bounds = layer.cogBounds;

      viewer.camera.setView({
        destination: new Cesium.Cartesian3.fromDegrees(
          (bounds[0] + bounds[2]) / 2,
          (bounds[1] + bounds[3]) / 2,
          2000
        ),
        orientation: {
          heading: Cesium.Math.toRadians(0),
          pitch: Cesium.Math.toRadians(-50),
          roll: 0.0,
        },
      });
    });
}

function handleLayerChange(value) {
  noBackground();
  if (value === "OSM") {
    useStreetLayer();
  } else if (value === "Satellite") {
    useSatelliteLayer();
  }
}

function noBackground() {
  streetsLayer.show = false;
  satelliteLayer.show = false;
  setAttribution(undefined);
}

function useStreetLayer() {
  streetsLayer.show = true;
  satelliteLayer.show = false;
  setAttribution(streetsLayer);
}

function useSatelliteLayer() {
  streetsLayer.show = false;
  satelliteLayer.show = true;
  setAttribution(satelliteLayer);
}

function setWireframe(enabled) {
  viewer.scene.globe._surface._tileProvider._debug.wireframe = enabled;
  updateViewer();
}

function useGridProvider(enabled) {
  gridLayer.show = enabled;
}

function useCoordinatesProvider(enabled) {
  coordinateLayer.show = enabled;
}

function updateViewer() {
  if (viewer && viewer.clock.shouldAnimate === false) {
    viewer.clock.shouldAnimate = true;
    viewer.clock.tick();
    viewer.clock.shouldAnimate = false;
  }
}

function setAttribution(layer) {
  credit = layer ? layer?._imageryProvider?._credit?._html : "";

  document.getElementById("attribution").innerText = credit;
}
