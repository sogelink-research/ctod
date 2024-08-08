function getUrlParamIgnoreCase(name) {
    const urlParams = new URLSearchParams(window.location.search);
    for (const [key, value] of urlParams.entries()) {
        if (key.toLowerCase() === name.toLowerCase()) {
            return value;
        }
    }
    return null;
  }
  