const HillshadingOptions = {
  enabled: true
};

const SlopeRampParams = {
  slopeRamp1: "0.0",
  slopeRamp2: "0.29",
  slopeRamp3: "0.5",
  slopeRamp4: "0.7",
  slopeRamp5: "0.87",
  slopeRamp6: "0.91",
  slopeRamp7: "1.0",
};

const SlopeRampColorParams = {
  slopeColor1: "rgba(0, 0, 0, 0.0)",
  slopeColor2: "rgba(0, 0, 0, 0.2)",
  slopeColor3: "rgba(0, 0, 0, 0.3)",
  slopeColor4: "rgba(0, 0, 0, 0.4)",
  slopeColor5: "rgba(0, 0, 0, 0.5)",
  slopeColor6: "rgba(0, 0, 0, 0.6)",
  slopeColor7: "rgba(0, 0, 0, 0.7)",
};

function getHillShadingSlopeRamp() {
  return Object.keys(SlopeRampParams).map((key) => SlopeRampParams[key]);
}

function getHillShadingSlopeRampColors() {
  return Object.keys(SlopeRampColorParams).map(
    (key) => SlopeRampColorParams[key]
  );
}

function disableHillshading() {
  viewer.scene.globe.material = undefined;
  updateViewer();
}

function setHillshading() {
  if (HillshadingOptions.enabled === false) {
    return;
  }

  const globe = viewer.scene.globe;
  var material = getSlopeMaterial();
  const shadingUniforms = material.uniforms;
  shadingUniforms.image = getSlopeColorRamp();

  globe.material = material;
  updateViewer();
}

function getSlopeColorRamp() {
  const values = getHillShadingSlopeRamp();
  const colors = getHillShadingSlopeRampColors();
  return createColorRamp(values, colors);
}

function createColorRamp(values, colors) {
  const ramp = document.createElement("canvas");
  ramp.width = 100;
  ramp.height = 1;
  const ctx = ramp.getContext("2d");
  const grd = ctx.createLinearGradient(0, 0, 100, 0);

  for (var i = 0; i < colors.length; i++) {
    grd.addColorStop(values[i], colors[i]);
  }

  ctx.fillStyle = grd;
  ctx.fillRect(0, 0, 100, 1);

  return ramp;
}

function getSlopeMaterial() {
  return Cesium.Material.fromType("SlopeRamp");
}
