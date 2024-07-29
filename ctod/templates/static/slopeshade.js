const HillshadingOptions = {
  enabled: true
};

const SlopeRampParams = {
  slopeRamp1: "0.0",
  slopeRamp2: "0.3",
  slopeRamp3: "0.5",
  slopeRamp4: "0.7",
  slopeRamp5: "0.9",
  slopeRamp6: "1.0",
};

const SlopeRampColorParams = {
  Color1: "rgba(0, 0, 0, 0.0)",
  Color2: "rgba(0, 0, 0, 0.1)",
  Color3: "rgba(0, 0, 0, 0.2)",
  Color4: "rgba(0, 0, 0, 0.3)",
  Color5: "rgba(0, 0, 0, 0.4)",
  Color6: "rgba(0, 0, 0, 0.5)",
};

function disableShading() {
  viewer.scene.globe.material = undefined;
  updateViewer();
}

function setShading() {
  if (HillshadingOptions.enabled === false) {
    return;
  }

  const material = Cesium.Material.fromType("SlopeRamp");
  material.uniforms.image = getSlopeColorRamp();
  viewer.scene.globe.material = material;
  updateViewer();
}

function getSlopeColorRamp() {
  const values = Object.values(SlopeRampParams).map((value) => parseFloat(value));
  const colors = Object.values(SlopeRampColorParams);
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