var viewer,
  terrainProvider,
  streetsLayer,
  satelliteLayer,
  gridLayer,
  coordinateLayer;
var currentCog;

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
  configureViewer();
  setShading();
}

function initializeLayers() {
  streetsLayer = createImageryLayer(
    "https://services.arcgisonline.com/arcgis/rest/services/World_Street_Map/MapServer"
  );
  satelliteLayer = createImageryLayer(
    "https://services.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer"
  );
  gridLayer = createImageryLayerWithProvider(new Cesium.GridImageryProvider());
  coordinateLayer = createImageryLayerWithProvider(
    new Cesium.TileCoordinatesImageryProvider()
  );

  gridLayer.show = false;
  coordinateLayer.show = false;

  const minZoom = getUrlParamIgnoreCase("minZoom") || 1;
  const maxZoom = getUrlParamIgnoreCase("maxZoom") || 18;
  const cog =
  getUrlParamIgnoreCase("cog") ||
    "./ctod/files/test_cog.tif";
  const skipCache = getUrlParamIgnoreCase("skipCache") || false;
  const meshingMethod = getUrlParamIgnoreCase("meshingMethod") || "grid";
  setTerrainProvider(minZoom, maxZoom, cog, "none", skipCache, meshingMethod);

  streetsLayer.show = true;
  satelliteLayer.show = false;

  [streetsLayer, satelliteLayer, gridLayer, coordinateLayer].forEach(
    (layer) => {
      viewer.imageryLayers.add(layer);
    }
  );
}

function createImageryLayer(url) {
  const provider = new Cesium.ArcGisMapServerImageryProvider({ url });
  return new Cesium.ImageryLayer(provider);
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
  //viewer.useBrowserRecommendedResolution = false;
  //viewer.resolutionScale = 1.0;
  //viewer.scene.globe.maximumScreenSpaceError = 1.33;
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

  // Remove cesiums ugly click
  viewer.cesiumWidget.screenSpaceEventHandler.setInputAction((e) => {
    // do nothing
  }, Cesium.ScreenSpaceEventType.LEFT_CLICK);

  viewer.camera.setView({
    destination: new Cesium.Cartesian3.fromDegrees(5.33195, 60.29969, 2000),
    orientation: {
      heading: Cesium.Math.toRadians(0),
      pitch: Cesium.Math.toRadians(-80),
      roll: 0.0,
    },
  });
}

function setTerrainProvider(minZoom, maxZoom, cog, resamplingMethod, skipCache, meshingMethod) {
  const terrainProviderUrl = `${window.location.origin}/tiles?minZoom=${minZoom}&maxZoom=${maxZoom}&cog=${cog}&skipCache=${skipCache}&meshingMethod=${meshingMethod}`;

  if (resamplingMethod !== "none") {
    terrainProviderUrl += `&resamplingMethod=${resamplingMethod}`;
  }

  terrainProvider = new Cesium.CesiumTerrainProvider({
    url: terrainProviderUrl,
    requestVertexNormals: true,
  });

  viewer.terrainProvider = terrainProvider;
  updateViewer();

  // go to cog location
  if (currentCog !== cog) {
    fetch(
      `${window.location.origin}/tiles/layer.json?maxZoom=${maxZoom}&cog=${cog}`
    )
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
  currentCog = cog;
}

function handleLayerChange(value) {
  noBackground();
  if (value === "Streets") {
    useStreetLayer();
  } else if (value === "Satellite") {
    useSatelliteLayer();
  }
}

function noBackground() {
  streetsLayer.show = false;
  satelliteLayer.show = false;
}

function useStreetLayer() {
  streetsLayer.show = true;
  satelliteLayer.show = false;
}

function useSatelliteLayer() {
  streetsLayer.show = false;
  satelliteLayer.show = true;
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
