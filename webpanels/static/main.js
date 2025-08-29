const domain = window.location.hostname;
const botName = document.getElementById("name");
const botDiscriminator = document.getElementById("discriminator");
const membersDiv = document.getElementById("member-count");
const commandsDiv = document.getElementById("command-count");
const latencyDiv = document.getElementById("latency");
const fancyErrorDiv = document.getElementById("fancy-error");
const fancySuccessDiv = document.getElementById("fancy-success");
const consoleDiv = document.getElementById("console");
const scrollContainer = document.querySelector(".console");
const cogContainer = document.getElementById("cog-list");
const startBtn = document.getElementById("start");
const stopBtn = document.getElementById("stop");
var wasBotOffline = false;

var isNotificationActive = false;

function fancyError(message) {
  if (isNotificationActive) {
    setTimeout(() => fancyError(message), 100);
    return;
  }

  isNotificationActive = true;
  fancyErrorDiv.classList.remove("d-none");
  fancyErrorDiv.innerHTML = message;

  setTimeout(() => {
    fancyErrorDiv.classList.add("d-none");
    fancyErrorDiv.innerHTML = "";
    isNotificationActive = false;
  }, 5000);
}

function fancySuccess(message) {
  if (isNotificationActive) {
    setTimeout(() => fancySuccess(message), 100);
    return;
  }

  fancySuccessDiv.classList.remove("d-none");
  fancySuccessDiv.innerHTML = message;

  setTimeout(() => {
    fancySuccessDiv.classList.add("d-none");
    fancySuccessDiv.innerHTML = "";
    isNotificationActive = false;
  }, 5000);
}

async function call_api(internal_api_url, params) {
  var response = fetch("/api", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      internal_api_url: internal_api_url,
      params: params,
    }),
  })
    .then((response) => response.json())
    .then((data) => {
      return data;
    });

  return response;
}

async function send_heartbeat() {
  const response = await fetch("/heartbeat");
  const data = await response.json();

  if (!data.alive) {
    wasBotOffline = true;
  }

  return data.alive;
}

async function toggleCog(cog, value) {
  var response = await call_api("/toggle_cog", { cog: cog, register: value });
  return response[0].registered;
}

function loadCogs(cogs) {
  var isAnyCogActive = false;

  // Only keep the original h1
  var h1 = cogContainer.querySelector("h1");

  // Reset the inner html re-append the first child
  cogContainer.innerHTML = "";
  cogContainer.appendChild(h1);

  cogs.forEach((cog) => {
    var wrapper = document.createElement("div");
    wrapper.classList.add("form-check", "fs-5", "me-5", "ms-4");

    var checkbox = document.createElement("input");
    checkbox.classList.add("form-check-input", "no-focus", "cog-checkbox");
    checkbox.type = "checkbox";
    checkbox.id = cog.name;
    checkbox.checked = cog.active;

    if (cog.active) {
      isAnyCogActive = true;
    }

    var label = document.createElement("label");
    label.classList.add("form-check-label");
    label.for = cog.name;
    label.innerText = cog.name;

    wrapper.appendChild(checkbox);
    wrapper.appendChild(label);

    cogContainer.appendChild(wrapper);
  });

  return isAnyCogActive;
}

//Add event listeners to stop and start.
stopBtn.addEventListener("click", () => {
  var result = call_api("/stop");

  if (!result.error) {
    fancySuccess("Successfully stopped the bot.");
  } else {
    fancyError(`Error shutting down: ${result.error}`);
  }
});

startBtn.addEventListener("click", () => {
  fetch("/start");

  // If you need to start the bot, the bot was probably offline
  wasBotOffline = true;
});

setInterval(async () => {
  var alive = await send_heartbeat();

  // If not alive means dead :(
  if (!alive) {
    startBtn.classList.remove("d-none");
    stopBtn.classList.add("d-none");
    document.title = "offline";
    latencyDiv.innerText = "--";
    membersDiv.innerText = "--";
    commandsDiv.innerText = "--";
    consoleDiv.innerHTML = "";
    return;
  }

  // If the bot has been offline, re-set the name and the cog list.
  if (wasBotOffline) {
    wasBotOffline = false;

    var name = await call_api("/bot-attribute", { attribute: "user.name" });
    var discriminator = await call_api("/bot-attribute", { attribute: "user.discriminator" });
    var cogs = await call_api("/cogs");

    if (name.value && discriminator.value) {
      document.title = name.value;
      botName.innerText = name.value;
      botDiscriminator.innerText = `#${discriminator.value}`;
      consoleDiv.innerHTML = "";
    } else {
      wasBotOffline = true;
      return;
    }

    if (cogs.error) {
      wasBotOffline = true;
      fancyError(`Error fetching cogs: ${cogs.error}`);
      return;
    }

    if (!cogs.cogs) {
      wasBotOffline = true;
      fancyError(`Error fetching cogs.`);
    }

    var isAnyCogActive = loadCogs(cogs.cogs);

    stopBtn.classList.remove("d-none");

    // Add every cog dynamically
    if (!isAnyCogActive) {
      let cogLoadInterval = setInterval(async () => {
        var cogs = await call_api("/cogs");

        if (cogs.error) {
          fancyError(cogs.error);
        }

        var isAnyCogActive = loadCogs(cogs.cogs);

        if (isAnyCogActive) {
          clearInterval(cogLoadInterval);
        }
      }, 2000);
    }
  }

  // Make the stop button appear
  stopBtn.classList.remove("d-none");

  // Hide the start button, the bot is alive
  startBtn.classList.add("d-none");

  // Update the latency
  var response = await call_api("/bot-attribute", { attribute: "latency" });

  if (response.attribute != "latency") {
    console.error(`400 response didn't have {attribute: "latency"}`);
    latencyDiv.innerText = "--";
  } else {
    var latency = parseFloat(response.value);

    if (typeof latency === "number" && !isNaN(latency)) {
      latencyDiv.innerText = `${latency.toFixed(2)}ms`;
    } else {
      latencyDiv.innerText = "--";
    }
  }

  // Update the command count
  var response = await call_api("/bot-attribute", { attribute: "tree.get_commands" });

  if (response.attribute != "tree.get_commands") {
    console.error(`400 response didn't have {attribute: "tree.get_commands"}`);
    commandsDiv.innerText = "--";
  } else {
    var commands = parseInt(response.count);

    if (typeof commands === "number" && !isNaN(commands)) {
      commandsDiv.innerText = commands;
    } else {
      commandsDiv.innerText = "--";
    }
  }

  //Update the member count
  var response = await call_api("/bot-attribute", { attribute: "get_all_members" });

  if (response.attribute != "get_all_members") {
    console.error(`400 response didn't have {attribute: "get_all_members"}`);
    commandsDiv.innerText = "--";
  } else {
    var members = parseInt(response.count);

    if (typeof members === "number" && !isNaN(members)) {
      membersDiv.innerText = members;
    } else {
      fancyError("Didn't receive a number for member count.");
      membersDiv.innerText = "--";
    }
  }

  //Update the console
  var response = await call_api("/logs", { "": "" });

  if (response[1] == 200) {
    var lines = response[0].lines;
    result = "";

    lines.forEach((line) => {
      result += `<p>${line}</p>`;
    });

    var should_scroll = scrollContainer.scrollTop == scrollContainer.scrollHeight;
    consoleDiv.innerHTML = result;

    if (should_scroll) {
      scrollContainer.scrollTop = scrollContainer.scrollHeight;
    }
  } else {
    fancyError(`${response[1]} ${response[0]}`);
  }
}, 2000);

document.querySelectorAll(".cog-checkbox").forEach((checkbox) => {
  checkbox.addEventListener("change", async (event) => {
    const cogName = event.target.id;
    const isChecked = event.target.checked;

    console.log(`${cogName} is now ${isChecked ? "enabled" : "disabled"}`);

    var new_checked = await toggleCog(cogName, isChecked);
    event.target.checked = new_checked;
    console.log(new_checked);
  });
});
