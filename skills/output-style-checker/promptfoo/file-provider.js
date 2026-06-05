const fs = require("node:fs");
const path = require("node:path");

module.exports = {
  id: "local-file-provider",
  callApi: async (prompt) => {
    const target = path.resolve(__dirname, "..", prompt.trim());
    const output = fs.readFileSync(target, "utf8");
    return {
      output
    };
  }
};

