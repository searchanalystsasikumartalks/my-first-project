"use strict";
(() => {
 const config = window.DIAGNOSTIC;
 const version = document.getElementById("version");
 const description = document.getElementById("description");
 const result = document.getElementById("result");
 let checks = 0;
 version.textContent = config.version;
 description.textContent = config.message;
 document.getElementById("check").addEventListener("click", () => {
   checks += 1;
   result.textContent = "Local script check passed. Runs: " + checks + ". " + config.version;
 });
 document.getElementById("reset").addEventListener("click", () => {
   checks = 0;
   result.textContent = "Ready. No information is collected or saved.";
 });
})();
