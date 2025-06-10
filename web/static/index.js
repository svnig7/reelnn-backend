
function switchTab(tabName) {
  
  document.querySelectorAll(".tab-content").forEach((tab) => {
    tab.classList.remove("active");
  });

  
  document.querySelectorAll(".tab-button").forEach((btn) => {
    btn.classList.remove("active");
  });

  
  document.getElementById(tabName + "-tab").classList.add("active");

  
  event.target.classList.add("active");
}


let currentUsers = [];
let currentEditingUser = null;


document.addEventListener("DOMContentLoaded", async function () {
  const token = localStorage.getItem("token");
  if (!token) {
    window.location.href = "/login";
    return;
  }

  try {
    const response = await fetch("/api/v1/auth-check", {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });

    if (!response.ok) {
      localStorage.removeItem("token");
      window.location.href = "/login";
      return;
    }

    document.getElementById("content").style.display = "block";
    await loadTrendingContent();
  } catch (error) {
    console.error("Authentication check failed:", error);
    localStorage.removeItem("token");
    window.location.href = "/login";
  }
});


async function fetchWithAuth(url, options = {}) {
  const token = localStorage.getItem("token");
  if (!token) {
    window.location.href = "/login";
    return null;
  }

  const headers = options.headers || {};
  headers["Authorization"] = `Bearer ${token}`;

  try {
    const response = await fetch(url, { ...options, headers });

    if (response.status === 401) {
      localStorage.removeItem("token");
      window.location.href = "/login";
      return null;
    }

    if (!response.ok) {
      const errorData = await response.text();
      console.error("API Error:", response.status, errorData);
      throw new Error(`HTTP ${response.status}: ${errorData}`);
    }

    return response;
  } catch (error) {
    console.error("Fetch error:", error);
    throw error;
  }
}

function logout() {
  localStorage.removeItem("token");
  window.location.href = "/login";
}


async function loadAllUsers() {
  try {
    const container = document.getElementById("users-container");
    container.innerHTML =
      '<div class="loading-text"><span class="spinner"></span> Loading users...</div>';

    const response = await fetchWithAuth("/api/v1/users?limit=500");
    if (!response) return;

    const data = await response.json();

    
    let users;
    if (Array.isArray(data)) {
      users = data;
    } else if (data.users && Array.isArray(data.users)) {
      users = data.users;
    } else {
      throw new Error("Invalid response format");
    }

    currentUsers = users;
    displayUsers(users);

    showNotification("success", `Loaded ${users.length} users`);
  } catch (error) {
    console.error("Load users error:", error);
    showNotification("error", `Failed to load users: ${error.message}`);
    document.getElementById("users-container").innerHTML =
      '<div class="loading-text">Failed to load users. Please try again.</div>';
  }
}

async function searchUsers(query) {
  if (!query.trim()) {
    displayUsers(currentUsers);
    return;
  }

  try {
    const response = await fetchWithAuth(
      `/api/v1/users/search?query=${encodeURIComponent(query)}`
    );
    if (!response) return;

    const data = await response.json();

    
    let users;
    if (Array.isArray(data)) {
      users = data;
    } else if (data.users && Array.isArray(data.users)) {
      users = data.users;
    } else {
      throw new Error("Invalid response format");
    }

    displayUsers(users);
  } catch (error) {
    console.error("Search users error:", error);
    showNotification("error", `Search failed: ${error.message}`);
  }
}

function displayUsers(users) {
  const container = document.getElementById("users-container");

  
  if (!Array.isArray(users)) {
    console.error("displayUsers: users is not an array:", users);
    container.innerHTML =
      '<div class="loading-text">Error: Invalid data format</div>';
    return;
  }

  if (users.length === 0) {
    container.innerHTML = '<div class="loading-text">No users found</div>';
    return;
  }

  const table = document.createElement("table");
  table.className = "users-table";

  table.innerHTML = `
                <thead>
                    <tr>
                        <th>User ID</th>
                        <th>Username</th>
                        <th>Name</th>
                        <th>Registration Date</th>
                        <th>Limit</th>
                        <th>Status</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody>
                    ${users
                      .map(
                        (user) => `
                        <tr>
                            <td>${user.user_id || "N/A"}</td>
                            <td>${user.username || "N/A"}</td>
                            <td>${
                              [user.first_name, user.last_name]
                                .filter(Boolean)
                                .join(" ") || "N/A"
                            }</td>
                            <td>${
                              user.registration_date
                                ? new Date(
                                    user.registration_date
                                  ).toLocaleDateString()
                                : "N/A"
                            }</td>
                            <td>${user.slimit || 0}</td>
                            <td>
                                <span class="user-status ${
                                  user.is_active !== false
                                    ? "status-active"
                                    : "status-inactive"
                                }">
                                    ${
                                      user.is_active !== false
                                        ? "Active"
                                        : "Inactive"
                                    }
                                </span>
                            </td>
                            <td class="user-actions">
                                <button class="btn-small btn-edit" onclick="openEditModal(${
                                  user.user_id
                                })">
                                    <i class="fas fa-edit"></i> Edit
                                </button>
                                <button class="btn-small btn-delete" onclick="deleteUser(${
                                  user.user_id
                                })">
                                    <i class="fas fa-trash"></i> Delete
                                </button>
                            </td>
                        </tr>
                    `
                      )
                      .join("")}
                </tbody>
            `;

  container.innerHTML = "";
  container.appendChild(table);
}

function openEditModal(userId) {
  const user = currentUsers.find((u) => u.user_id === userId);
  if (!user) {
    showNotification("error", "User not found");
    return;
  }

  currentEditingUser = user;

  
  document.getElementById("edit-user-id").value = user.user_id;
  document.getElementById("edit-username").value = user.username || "";
  document.getElementById("edit-first-name").value = user.first_name || "";
  document.getElementById("edit-last-name").value = user.last_name || "";
  document.getElementById("edit-slimit").value = user.slimit || 0;
  document.getElementById("edit-is-active").value = user.is_active
    ? "true"
    : "false";

  
  document.getElementById("edit-user-modal").style.display = "block";
}

function closeEditModal() {
  document.getElementById("edit-user-modal").style.display = "none";
  currentEditingUser = null;
}

async function saveUserChanges(event) {
  event.preventDefault();

  if (!currentEditingUser) return;

  try {
    const saveIcon = document.getElementById("save-user-icon");
    const saveLoading = document.getElementById("save-user-loading");
    const saveBtn = document.getElementById("save-user-btn");

    
    saveIcon.style.display = "none";
    saveLoading.style.display = "inline-block";
    saveBtn.disabled = true;

    const updateData = {
      username: document.getElementById("edit-username").value || null,
      first_name: document.getElementById("edit-first-name").value || null,
      last_name: document.getElementById("edit-last-name").value || null,
      slimit: parseInt(document.getElementById("edit-slimit").value) || 0,
      is_active: document.getElementById("edit-is-active").value === "true",
    };

    const response = await fetchWithAuth(
      `/api/v1/users/${currentEditingUser.user_id}`,
      {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(updateData),
      }
    );

    if (!response) return;

    const result = await response.json();

    
    saveIcon.style.display = "inline-block";
    saveLoading.style.display = "none";
    saveBtn.disabled = false;

    if (response.ok) {
      showNotification("success", "User updated successfully");
      closeEditModal();
      
      await refreshUsers();
    } else {
      showNotification("error", result.message || "Failed to update user");
    }
  } catch (error) {
    showNotification("error", `Update failed: ${error.message}`);

    
    const saveIcon = document.getElementById("save-user-icon");
    const saveLoading = document.getElementById("save-user-loading");
    const saveBtn = document.getElementById("save-user-btn");

    saveIcon.style.display = "inline-block";
    saveLoading.style.display = "none";
    saveBtn.disabled = false;
  }
}

async function deleteUser(userId) {
  if (
    !confirm(
      "Are you sure you want to delete this user? This action cannot be undone."
    )
  ) {
    return;
  }

  try {
    const response = await fetchWithAuth(`/api/v1/users/${userId}`, {
      method: "DELETE",
    });

    if (!response) return;

    const result = await response.json();

    if (response.ok) {
      showNotification("success", "User deleted successfully");
      
      currentUsers = currentUsers.filter((u) => u.user_id !== userId);
      displayUsers(currentUsers);
    } else {
      showNotification("error", result.message || "Failed to delete user");
    }
  } catch (error) {
    showNotification("error", `Delete failed: ${error.message}`);
  }
}

async function refreshUsers() {
  const searchValue = document.getElementById("user-search").value.trim();
  if (searchValue) {
    await searchUsers(searchValue);
  } else if (currentUsers.length > 0) {
    await loadAllUsers();
  }
}


document.getElementById("user-search").addEventListener(
  "input",
  debounce(function (e) {
    const query = e.target.value.trim();
    if (query.length >= 1) {
      searchUsers(query);
    } else {
      displayUsers(currentUsers);
    }
  }, 500)
);


document
  .getElementById("edit-user-form")
  .addEventListener("submit", saveUserChanges);


window.addEventListener("click", function (event) {
  const modal = document.getElementById("edit-user-modal");
  if (event.target === modal) {
    closeEditModal();
  }
});



const trendingItems = {
  movie: [],
  show: [],
};


const movieSearchInput = document.getElementById("movie-search");
const movieSearchBtn = document.getElementById("movie-search-btn");
const movieResults = document.getElementById("movie-results");
const showSearchInput = document.getElementById("show-search");
const showSearchBtn = document.getElementById("show-search-btn");
const showResults = document.getElementById("show-results");
const saveBtn = document.getElementById("save-trending");
const saveIcon = document.getElementById("save-icon");
const saveLoading = document.getElementById("save-loading");


movieSearchInput.addEventListener(
  "input",
  debounce(function (e) {
    if (e.target.value.length >= 2) {
      searchMedia("movie", e.target.value);
    } else {
      movieResults.innerHTML = "";
    }
  }, 500)
);


movieSearchBtn.addEventListener("click", function () {
  if (movieSearchInput.value.length >= 2) {
    searchMedia("movie", movieSearchInput.value);
  }
});


movieSearchInput.addEventListener("keypress", function (e) {
  if (e.key === "Enter" && this.value.length >= 2) {
    searchMedia("movie", this.value);
  }
});


showSearchInput.addEventListener(
  "input",
  debounce(function (e) {
    if (e.target.value.length >= 2) {
      searchMedia("show", e.target.value);
    } else {
      showResults.innerHTML = "";
    }
  }, 500)
);


showSearchBtn.addEventListener("click", function () {
  if (showSearchInput.value.length >= 2) {
    searchMedia("show", showSearchInput.value);
  }
});


showSearchInput.addEventListener("keypress", function (e) {
  if (e.key === "Enter" && this.value.length >= 2) {
    searchMedia("show", this.value);
  }
});


saveBtn.addEventListener("click", function () {
  saveTrendingConfiguration();
});


function debounce(func, wait) {
  let timeout;
  return function () {
    const context = this;
    const args = arguments;
    clearTimeout(timeout);
    timeout = setTimeout(() => {
      func.apply(context, args);
    }, wait);
  };
}


async function searchMedia(mediaType, query) {
  try {
    
    const resultsElement = mediaType === "movie" ? movieResults : showResults;
    resultsElement.innerHTML =
      '<div class="loading-text"><span class="spinner"></span> Searching...</div>';

    
    const searchBtn = mediaType === "movie" ? movieSearchBtn : showSearchBtn;
    searchBtn.disabled = true;

    const response = await fetchWithAuth(
      `/api/v1/search/${mediaType}?query=${encodeURIComponent(query)}`
    );
    if (!response) return;
    const data = await response.json();

    
    searchBtn.disabled = false;

    if (response.ok) {
      displaySearchResults(mediaType, data);
    } else {
      showNotification(
        "error",
        `Error: ${data.detail || "Failed to search for content"}`
      );
      resultsElement.innerHTML =
        '<div class="loading-text">Search failed. Please try again.</div>';
    }
  } catch (error) {
    showNotification("error", `Error: ${error.message}`);
    const resultsElement = mediaType === "movie" ? movieResults : showResults;
    resultsElement.innerHTML =
      '<div class="loading-text">Search failed. Please try again.</div>';

    
    const searchBtn = mediaType === "movie" ? movieSearchBtn : showSearchBtn;
    searchBtn.disabled = false;
  }
}


function displaySearchResults(mediaType, results) {
  const resultsElement = mediaType === "movie" ? movieResults : showResults;
  resultsElement.innerHTML = "";

  if (results.length === 0) {
    resultsElement.innerHTML =
      '<div class="loading-text">No results found</div>';
    return;
  }

  results.forEach((item) => {
    const resultItem = document.createElement("div");
    resultItem.className = "result-item";

    
    const isSelected = trendingItems[mediaType].some((i) => i.id === item.id);

    resultItem.innerHTML = `
                    <img src="https:
                      item.poster
                    }" onerror="this.src='https:
                    <div>
                        <strong>${item.title}</strong>
                        ${item.year ? ` (${item.year})` : ""}
                        <br>
                        Rating: ${item.vote_average}/10
                    </div>
                `;

    if (!isSelected) {
      resultItem.addEventListener("click", function () {
        addToTrending(mediaType, item);
      });
    } else {
      resultItem.style.opacity = "0.5";
      resultItem.style.cursor = "default";
      resultItem.title = "Already added to trending";
    }

    resultsElement.appendChild(resultItem);
  });
}


function addToTrending(mediaType, item) {
  
  if (trendingItems[mediaType].some((i) => i.id === item.id)) {
    return;
  }

  trendingItems[mediaType].push(item);
  updateTrendingDisplay(mediaType);

  
  showNotification("success", `Added ${item.title} to trending ${mediaType}s`);

  
  const searchInput =
    mediaType === "movie" ? movieSearchInput : showSearchInput;
  if (searchInput.value.length >= 2) {
    searchMedia(mediaType, searchInput.value);
  }
}


function removeFromTrending(mediaType, itemId) {
  const removedItem = trendingItems[mediaType].find(
    (item) => item.id === itemId
  );
  trendingItems[mediaType] = trendingItems[mediaType].filter(
    (item) => item.id !== itemId
  );
  updateTrendingDisplay(mediaType);

  
  if (removedItem) {
    showNotification(
      "success",
      `Removed ${removedItem.title} from trending ${mediaType}s`
    );
  }

  
  const searchInput =
    mediaType === "movie" ? movieSearchInput : showSearchInput;
  if (searchInput.value.length >= 2) {
    searchMedia(mediaType, searchInput.value);
  }
}


function updateTrendingDisplay(mediaType) {
  const trendingElement = document.getElementById(`trending-${mediaType}s`);
  trendingElement.innerHTML = "";

  if (trendingItems[mediaType].length === 0) {
    trendingElement.innerHTML = "<p>No items selected</p>";
    return;
  }

  trendingItems[mediaType].forEach((item) => {
    const trendingItem = document.createElement("div");
    trendingItem.className = "trending-item";
    trendingItem.innerHTML = `
                    <img src="https:
                      item.poster
                    }" onerror="this.src='https:
                    <div>
                        <strong>${item.title}</strong>
                        ${item.year ? ` (${item.year})` : ""}
                        <br>
                        Rating: ${item.vote_average}/10
                    </div>
                    <div class="trending-controls">
                        <button class="remove-btn" title="Remove from trending"><i class="fas fa-trash"></i></button>
                    </div>
                `;

    trendingItem
      .querySelector(".remove-btn")
      .addEventListener("click", function () {
        removeFromTrending(mediaType, item.id);
      });

    trendingElement.appendChild(trendingItem);
  });
}


async function saveTrendingConfiguration() {
  try {
    
    saveIcon.style.display = "none";
    saveLoading.style.display = "inline-block";
    saveBtn.disabled = true;

    
    const payload = {
      movie: trendingItems.movie.map((item) => item.id),
      show: trendingItems.show.map((item) => item.id),
    };

    const response = await fetchWithAuth("/api/v1/update_trending", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    });
    if (!response) return;
    const data = await response.json();

    
    saveIcon.style.display = "inline-block";
    saveLoading.style.display = "none";
    saveBtn.disabled = false;

    if (response.ok) {
      showNotification("success", "Trending configuration saved successfully!");

      
      await loadTrendingContent();
    } else {
      showNotification(
        "error",
        `Error: ${data.detail || "Failed to save trending configuration"}`
      );
    }
  } catch (error) {
    
    saveIcon.style.display = "inline-block";
    saveLoading.style.display = "none";
    saveBtn.disabled = false;

    showNotification("error", `Error: ${error.message}`);
  }
}


function showNotification(type, message, duration = 5000) {
  
  let container = document.getElementById("notifications-container");
  if (!container) {
    container = document.createElement("div");
    container.id = "notifications-container";
    container.className = "notifications-container";
    document.body.appendChild(container);
  }

  
  const notification = document.createElement("div");
  notification.className = `notification ${type}`;

  
  let icon = "info-circle";
  if (type === "success") icon = "check-circle";
  if (type === "error") icon = "exclamation-circle";

  
  notification.innerHTML = `
                <div class="notification-content">
                    <div class="notification-icon">
                        <i class="fas fa-${icon}"></i>
                    </div>
                    <div class="notification-message">${message}</div>
                    <div class="notification-close">
                        <i class="fas fa-times"></i>
                    </div>
                </div>
                <div class="notification-progress">
                    <div class="notification-progress-bar"></div>
                </div>
            `;

  
  container.appendChild(notification);

  
  const closeBtn = notification.querySelector(".notification-close");
  closeBtn.addEventListener("click", () => {
    removeNotification(notification);
  });

  
  setTimeout(() => {
    removeNotification(notification);
  }, duration);

  
  function removeNotification(notif) {
    if (notif.classList.contains("removing")) return;

    notif.classList.add("removing");
    notif.addEventListener("animationend", () => {
      if (notif.parentNode) {
        notif.parentNode.removeChild(notif);
      }
    });
  }

  return notification;
}


updateTrendingDisplay("movie");
updateTrendingDisplay("show");


async function loadTrendingContent() {
  try {
    const response = await fetchWithAuth("/api/v1/trending");
    if (!response) return;

    const data = await response.json();

    
    trendingItems.movie = [];
    trendingItems.show = [];

    
    const movies = data.filter((item) => item.media_type === "movie");
    movies.forEach((movie) => {
      const processedMovie = {
        id: movie.id,
        title: movie.title,
        poster: movie.poster,
        vote_average: movie.vote_average,
        year: movie.year,
        media_type: "movie",
      };
      trendingItems.movie.push(processedMovie);
    });

    
    const shows = data.filter((item) => item.media_type === "show");
    shows.forEach((show) => {
      const processedShow = {
        id: show.id,
        title: show.title,
        poster: show.poster,
        vote_average: show.vote_average,
        year: show.year,
        media_type: "show",
      };
      trendingItems.show.push(processedShow);
    });

    
    updateTrendingDisplay("movie");
    updateTrendingDisplay("show");

    showNotification("success", "Trending content loaded");
  } catch (error) {
    console.error("Error loading trending content:", error);
    showNotification(
      "error",
      `Failed to load trending content: ${error.message}`
    );
  }
}


async function refreshTrendingContent(mediaType) {
  try {
    showNotification("success", `Refreshing trending ${mediaType}s...`);
    await loadTrendingContent();
  } catch (error) {
    showNotification(
      "error",
      `Failed to refresh trending ${mediaType}s: ${error.message}`
    );
  }
}


document
  .getElementById("refresh-trending-movies")
  .addEventListener("click", function () {
    refreshTrendingContent("movie");
  });

document
  .getElementById("refresh-trending-shows")
  .addEventListener("click", function () {
    refreshTrendingContent("show");
  });


let currentContent = null;
let currentContentType = "movie";


document.querySelectorAll('input[name="content-type"]').forEach((radio) => {
  radio.addEventListener("change", function () {
    currentContentType = this.value;
    document.getElementById("content-id-input").placeholder =
      this.value === "movie"
        ? "Enter Movie ID (mid)..."
        : "Enter Show ID (sid)...";

    
    document.getElementById("content-editor").style.display = "none";
    currentContent = null;
  });
});

document
  .getElementById("load-content-btn")
  .addEventListener("click", loadContent);
document
  .getElementById("content-id-input")
  .addEventListener("keypress", function (e) {
    if (e.key === "Enter") {
      loadContent();
    }
  });

document
  .getElementById("save-content-btn")
  .addEventListener("click", saveContentChanges);


async function loadContent() {
  const contentId = document.getElementById("content-id-input").value.trim();

  if (!contentId) {
    showNotification("error", "Please enter a valid ID");
    return;
  }

  try {
    const loadBtn = document.getElementById("load-content-btn");
    loadBtn.disabled = true;
    loadBtn.innerHTML = '<span class="spinner"></span> Loading...';

    const endpoint =
      currentContentType === "movie"
        ? `/api/v1/getMovieDetails/${contentId}`
        : `/api/v1/getShowDetails/${contentId}`;

    const response = await fetchWithAuth(endpoint);
    if (!response) return;

    if (response.ok) {
      const data = await response.json();
      currentContent = data;
      populateContentForm(data);
      document.getElementById("content-editor").style.display = "block";
      showNotification(
        "success",
        `${
          currentContentType === "movie" ? "Movie" : "Show"
        } loaded successfully`
      );
    } else {
      const error = await response.json();
      showNotification(
        "error",
        `Failed to load content: ${error.detail || "Not found"}`
      );
    }
  } catch (error) {
    showNotification("error", `Error loading content: ${error.message}`);
  } finally {
    const loadBtn = document.getElementById("load-content-btn");
    loadBtn.disabled = false;
    loadBtn.innerHTML = '<i class="fas fa-search"></i> Load Content';
  }
}


function populateContentForm(content) {
  document.getElementById("content-title").textContent = `Edit ${
    currentContentType === "movie" ? "Movie" : "Show"
  }: ${content.title}`;

  
  document.getElementById("edit-content-id").value =
    content.id || content.mid || content.sid || "";
  document.getElementById("edit-title").value = content.title || "";
  document.getElementById("edit-original-title").value =
    content.original_title || "";
  document.getElementById("edit-release-date").value =
    content.release_date || "";
  document.getElementById("edit-overview").value = content.overview || "";
  document.getElementById("edit-poster-path").value = content.poster_path || "";
  document.getElementById("edit-backdrop-path").value =
    content.backdrop_path || "";
  document.getElementById("edit-logo").value = content.logo || "";
  document.getElementById("edit-trailer").value = content.trailer || "";
  document.getElementById("edit-vote-average").value =
    content.vote_average || "";
  document.getElementById("edit-vote-count").value = content.vote_count || "";
  document.getElementById("edit-popularity").value = content.popularity || "";

  
  document.getElementById("edit-genres").value = Array.isArray(content.genres)
    ? content.genres.join(", ")
    : content.genres || "";
  document.getElementById("edit-studios").value = Array.isArray(content.studios)
    ? content.studios.join(", ")
    : content.studios || "";
  document.getElementById("edit-links").value = Array.isArray(content.links)
    ? content.links.join(", ")
    : content.links || "";

  
  if (currentContentType === "movie") {
    document.getElementById("runtime-group").style.display = "block";
    document.getElementById("directors-group").style.display = "block";
    document.getElementById("creators-group").style.display = "none";
    document.getElementById("show-specific").style.display = "none";
    document.getElementById("movie-quality-section").style.display = "block";
    document.getElementById("show-seasons-section").style.display = "none";

    document.getElementById("edit-runtime").value = content.runtime || "";
    document.getElementById("edit-directors").value = Array.isArray(
      content.directors
    )
      ? content.directors.join(", ")
      : content.directors || "";

    
    populateMovieQualities(content.quality || []);
  } else {
    document.getElementById("runtime-group").style.display = "none";
    document.getElementById("directors-group").style.display = "none";
    document.getElementById("creators-group").style.display = "block";
    document.getElementById("show-specific").style.display = "block";
    document.getElementById("movie-quality-section").style.display = "none";
    document.getElementById("show-seasons-section").style.display = "block";

    document.getElementById("edit-creators").value = Array.isArray(
      content.creators
    )
      ? content.creators.join(", ")
      : content.creators || "";
    document.getElementById("edit-total-seasons").value =
      content.total_seasons || "";
    document.getElementById("edit-total-episodes").value =
      content.total_episodes || "";
    document.getElementById("edit-status").value = content.status || "";

    
    populateShowSeasons(content.season || []);
  }
}


function populateMovieQualities(qualities) {
  const container = document.getElementById("movie-qualities-container");
  container.innerHTML = "";

  qualities.forEach((quality, index) => {
    addMovieQualityItem(quality, index);
  });
}


function addMovieQualityItem(quality = {}, index = null) {
  const container = document.getElementById("movie-qualities-container");
  const qualityIndex = index !== null ? index : container.children.length;

  const qualityDiv = document.createElement("div");
  qualityDiv.className = "quality-item";
  qualityDiv.dataset.index = qualityIndex;

  qualityDiv.innerHTML = `
        <h5>
            Quality Option ${qualityIndex + 1}
            <button type="button" class="remove-item-btn" onclick="removeMovieQuality(${qualityIndex})">
                <i class="fas fa-trash"></i>
            </button>
        </h5>
        <div class="form-row">
            <div class="form-group">
                <label>Quality Type</label>
                <input type="text" name="quality_type_${qualityIndex}" value="${
    quality.type || ""
  }" placeholder="1080p, 4K, etc.">
            </div>
            <div class="form-group">
                <label>File Size</label>
                <input type="text" name="quality_size_${qualityIndex}" value="${
    quality.size || ""
  }" placeholder="2.5 GB">
            </div>
        </div>
        <div class="form-row">
            <div class="form-group">
                <label>Audio Language</label>
                <input type="text" name="quality_audio_${qualityIndex}" value="${
    quality.audio || ""
  }" placeholder="English">
            </div>
            <div class="form-group">
                <label>Video Codec</label>
                <input type="text" name="quality_codec_${qualityIndex}" value="${
    quality.video_codec || ""
  }" placeholder="H.264, H.265">
            </div>
        </div>
        <div class="form-row">
            <div class="form-group">
                <label>File Type</label>
                <input type="text" name="quality_file_type_${qualityIndex}" value="${
    quality.file_type || ""
  }" placeholder="mp4, mkv">
            </div>
            <div class="form-group">
                <label>Subtitle Language</label>
                <input type="text" name="quality_subtitle_${qualityIndex}" value="${
    quality.subtitle || ""
  }" placeholder="English">
            </div>
        </div>
        <div class="form-row">
            <div class="form-group">
                <label>Message ID</label>
                <input type="number" name="quality_msg_id_${qualityIndex}" value="${
    quality.msg_id || ""
  }" placeholder="Message ID">
            </div>
            <div class="form-group">
                <label>Chat ID</label>
                <input type="number" name="quality_chat_id_${qualityIndex}" value="${
    quality.chat_id || ""
  }" placeholder="Chat ID">
            </div>
        </div>
    `;

  container.appendChild(qualityDiv);
}


function removeMovieQuality(index) {
  const qualityItem = document.querySelector(`[data-index="${index}"]`);
  if (qualityItem) {
    qualityItem.remove();
  }
}


function populateShowSeasons(seasons) {
  const container = document.getElementById("seasons-container");
  container.innerHTML = "";

  seasons.forEach((season, index) => {
    addSeasonItem(season, index);
  });
}


function addSeasonItem(season = {}, index = null) {
  const container = document.getElementById("seasons-container");
  const seasonIndex = index !== null ? index : container.children.length;

  const seasonDiv = document.createElement("div");
  seasonDiv.className = "season-item";
  seasonDiv.dataset.season = seasonIndex;

  seasonDiv.innerHTML = `
        <h5 class="collapsible" onclick="toggleCollapsible(this)">
            <span>Season ${season.season_number || seasonIndex + 1} (${
    (season.episodes || []).length
  } episodes)</span>
            <div>
                <button type="button" class="btn-small" style="background-color: #17a2b8;" onclick="event.stopPropagation(); addEpisodeItem(${seasonIndex})">
                    <i class="fas fa-plus"></i> Add Episode
                </button>
                <button type="button" class="remove-item-btn" onclick="event.stopPropagation(); removeSeason(${seasonIndex})">
                    <i class="fas fa-trash"></i>
                </button>
            </div>
        </h5>
        <div class="collapsible-content">
            <div class="form-group">
                <label>Season Number</label>
                <input type="number" name="season_number_${seasonIndex}" value="${
    season.season_number || seasonIndex + 1
  }" min="1">
            </div>
            <div class="episodes-container" id="episodes-container-${seasonIndex}">
                <!-- Episodes will be populated here -->
            </div>
        </div>
    `;

  container.appendChild(seasonDiv);

  
  if (season.episodes) {
    season.episodes.forEach((episode, episodeIndex) => {
      addEpisodeItem(seasonIndex, episode, episodeIndex);
    });
  }
}


function addEpisodeItem(seasonIndex, episode = {}, episodeIndex = null) {
  const container = document.getElementById(
    `episodes-container-${seasonIndex}`
  );
  const epIndex =
    episodeIndex !== null ? episodeIndex : container.children.length;

  const episodeDiv = document.createElement("div");
  episodeDiv.className = "episode-item";
  episodeDiv.dataset.episode = epIndex;

  episodeDiv.innerHTML = `
        <h5 class="collapsible" onclick="toggleCollapsible(this)">
            <span>Episode ${episode.episode_number || epIndex + 1}: ${
    episode.name || "Untitled"
  }</span>
            <div>
                <button type="button" class="btn-small" style="background-color: #28a745;" onclick="event.stopPropagation(); addEpisodeQuality(${seasonIndex}, ${epIndex})">
                    <i class="fas fa-plus"></i> Add Quality
                </button>
                <button type="button" class="remove-item-btn" onclick="event.stopPropagation(); removeEpisode(${seasonIndex}, ${epIndex})">
                    <i class="fas fa-trash"></i>
                </button>
            </div>
        </h5>
        <div class="collapsible-content">
            <div class="form-row">
                <div class="form-group">
                    <label>Episode Number</label>
                    <input type="number" name="episode_number_${seasonIndex}_${epIndex}" value="${
    episode.episode_number || epIndex + 1
  }" min="1">
                </div>
                <div class="form-group">
                    <label>Episode Name</label>
                    <input type="text" name="episode_name_${seasonIndex}_${epIndex}" value="${
    episode.name || ""
  }" placeholder="Episode title">
                </div>
            </div>
            <div class="form-row">
                <div class="form-group">
                    <label>Air Date</label>
                    <input type="date" name="episode_air_date_${seasonIndex}_${epIndex}" value="${
    episode.air_date || ""
  }">
                </div>
                                                                                           <div class="form-group">
                    <label>Still Path</label>
                    <input type="text" name="episode_still_path_${seasonIndex}_${epIndex}" value="${
    episode.still_path || ""
  }" placeholder="Episode image path">
                </div>
            </div>
            <div class="form-group">
                <label>Episode Overview</label>
                <textarea name="episode_overview_${seasonIndex}_${epIndex}" rows="3" placeholder="Episode description">${
    episode.overview || ""
  }</textarea>
            </div>
            <div class="episode-qualities-container" id="episode-qualities-${seasonIndex}-${epIndex}">
                <h6>Quality Options</h6>
                <!-- Episode qualities will be populated here -->
            </div>
        </div>
    `;

  container.appendChild(episodeDiv);

  
  if (episode.quality) {
    episode.quality.forEach((quality, qualityIndex) => {
      addEpisodeQuality(seasonIndex, epIndex, quality, qualityIndex);
    });
  }
}


function addEpisodeQuality(
  seasonIndex,
  episodeIndex,
  quality = {},
  qualityIndex = null
) {
  const container = document.getElementById(
    `episode-qualities-${seasonIndex}-${episodeIndex}`
  );
  const qIndex =
    qualityIndex !== null ? qualityIndex : container.children.length - 1; 

  const qualityDiv = document.createElement("div");
  qualityDiv.className = "quality-item";
  qualityDiv.dataset.quality = qIndex;

  qualityDiv.innerHTML = `
        <h5>
            Quality ${qIndex + 1}
            <button type="button" class="remove-item-btn" onclick="removeEpisodeQuality(${seasonIndex}, ${episodeIndex}, ${qIndex})">
                <i class="fas fa-trash"></i>
            </button>
        </h5>
        <div class="form-row">
            <div class="form-group">
                <label>Quality Type</label>
                <input type="text" name="ep_quality_type_${seasonIndex}_${episodeIndex}_${qIndex}" value="${
    quality.type || ""
  }" placeholder="1080p, 4K">
            </div>
            <div class="form-group">
                <label>File Size</label>
                <input type="text" name="ep_quality_size_${seasonIndex}_${episodeIndex}_${qIndex}" value="${
    quality.size || ""
  }" placeholder="500 MB">
            </div>
        </div>
        <div class="form-row">
            <div class="form-group">
                <label>Audio Language</label>
                <input type="text" name="ep_quality_audio_${seasonIndex}_${episodeIndex}_${qIndex}" value="${
    quality.audio || ""
  }" placeholder="English">
            </div>
            <div class="form-group">
                <label>Video Codec</label>
                <input type="text" name="ep_quality_codec_${seasonIndex}_${episodeIndex}_${qIndex}" value="${
    quality.video_codec || ""
  }" placeholder="H.264">
            </div>
        </div>
        <div class="form-row">
            <div class="form-group">
                <label>File Type</label>
                <input type="text" name="ep_quality_file_type_${seasonIndex}_${episodeIndex}_${qIndex}" value="${
    quality.file_type || ""
  }" placeholder="mp4">
            </div>
            <div class="form-group">
                <label>Subtitle</label>
                <input type="text" name="ep_quality_subtitle_${seasonIndex}_${episodeIndex}_${qIndex}" value="${
    quality.subtitle || ""
  }" placeholder="English">
            </div>
        </div>
        <div class="form-row">
            <div class="form-group">
                <label>Runtime (minutes)</label>
                <input type="number" name="ep_quality_runtime_${seasonIndex}_${episodeIndex}_${qIndex}" value="${
    quality.runtime || ""
  }" min="1">
            </div>
            <div class="form-group">
                <label>Message ID</label>
                <input type="number" name="ep_quality_msg_id_${seasonIndex}_${episodeIndex}_${qIndex}" value="${
    quality.msg_id || ""
  }">
            </div>
        </div>
        <div class="form-row">
            <div class="form-group">
                <label>Chat ID</label>
                <input type="number" name="ep_quality_chat_id_${seasonIndex}_${episodeIndex}_${qIndex}" value="${
    quality.chat_id || ""
  }">
            </div>
            <div class="form-group">
                <label>File Hash</label>
                <input type="text" name="ep_quality_file_hash_${seasonIndex}_${episodeIndex}_${qIndex}" value="${
    quality.file_hash || ""
  }">
            </div>
        </div>
    `;

  container.appendChild(qualityDiv);

  
  if (qualityIndex === null) {
    setTimeout(() => {
      qualityDiv.scrollIntoView({
        behavior: "smooth",
        block: "nearest",
        inline: "nearest",
      });
    }, 100);
  }
}


function expandAllSections() {
  document.querySelectorAll(".collapsible-content").forEach((content) => {
    content.classList.add("active");
  });
}


function collapseAllSections() {
  document.querySelectorAll(".collapsible-content").forEach((content) => {
    content.classList.remove("active");
  });
}




function toggleCollapsible(element) {
  const content = element.nextElementSibling;
  const isActive = content.classList.contains("active");

  if (isActive) {
    content.classList.remove("active");
  } else {
    content.classList.add("active");

    
    setTimeout(() => {
      const rect = content.getBoundingClientRect();
      const containerRect = document
        .getElementById("content-editor")
        .getBoundingClientRect();

      
      if (rect.bottom > containerRect.bottom) {
        content.scrollIntoView({
          behavior: "smooth",
          block: "nearest",
          inline: "nearest",
        });
      }
    }, 300); 
  }
}


async function saveContentChanges() {
  if (!currentContent) {
    showNotification('error', 'No content loaded');
    return;
  }

  try {
    const saveIcon = document.getElementById('save-content-icon');
    const saveLoading = document.getElementById('save-content-loading');
    const saveBtn = document.getElementById('save-content-btn');

    
    saveIcon.style.display = 'none';
    saveLoading.style.display = 'inline-block';
    saveBtn.disabled = true;

    
    const updateData = {
      title: document.getElementById('edit-title').value,
      original_title: document.getElementById('edit-original-title').value,
      release_date: document.getElementById('edit-release-date').value || null,
      overview: document.getElementById('edit-overview').value,
      poster_path: document.getElementById('edit-poster-path').value,
      backdrop_path: document.getElementById('edit-backdrop-path').value,
      logo: document.getElementById('edit-logo').value,
      trailer: document.getElementById('edit-trailer').value,
      vote_average: parseFloat(document.getElementById('edit-vote-average').value) || null,
      vote_count: parseInt(document.getElementById('edit-vote-count').value) || null,
      popularity: parseFloat(document.getElementById('edit-popularity').value) || null,
      genres: document.getElementById('edit-genres').value.split(',').map(g => g.trim()).filter(g => g),
      studios: document.getElementById('edit-studios').value.split(',').map(s => s.trim()).filter(s => s),
      links: document.getElementById('edit-links').value.split(',').map(l => l.trim()).filter(l => l)
    };

    
    if (currentContentType === 'movie') {
      updateData.runtime = parseInt(document.getElementById('edit-runtime').value) || null;
      updateData.directors = document.getElementById('edit-directors').value.split(',').map(d => d.trim()).filter(d => d);
      
      
      updateData.quality = collectMovieQualities();
    } else {
      updateData.creators = document.getElementById('edit-creators').value.split(',').map(c => c.trim()).filter(c => c);
      updateData.total_seasons = parseInt(document.getElementById('edit-total-seasons').value) || null;
      updateData.total_episodes = parseInt(document.getElementById('edit-total-episodes').value) || null;
      updateData.status = document.getElementById('edit-status').value;
      
      
      updateData.season = collectShowSeasons();
    }

    
    Object.keys(updateData).forEach(key => {
      if (updateData[key] === null || updateData[key] === '' || 
          (Array.isArray(updateData[key]) && updateData[key].length === 0)) {
        delete updateData[key];
      }
    });

    console.log('Sending update data:', updateData); 

    const contentId = currentContent.id || currentContent.mid || currentContent.sid;
    const endpoint = `/api/v1/update${currentContentType === 'movie' ? 'Movie' : 'Show'}/${contentId}`;

    const response = await fetchWithAuth(endpoint, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(updateData)
    });

    
    saveIcon.style.display = 'inline-block';
    saveLoading.style.display = 'none';
    saveBtn.disabled = false;

    if (response && response.ok) {
      const result = await response.json();
      showNotification('success', `${currentContentType === 'movie' ? 'Movie' : 'Show'} updated successfully`);
      
      
      await loadContent();
    } else {
      const error = await response.json();
      showNotification('error', `Update failed: ${error.detail || 'Unknown error'}`);
    }
  } catch (error) {
    console.error('Save error:', error);
    showNotification('error', `Update failed: ${error.message}`);
    
    
    const saveIcon = document.getElementById('save-content-icon');
    const saveLoading = document.getElementById('save-content-loading');
    const saveBtn = document.getElementById('save-content-btn');
    
    saveIcon.style.display = 'inline-block';
    saveLoading.style.display = 'none';
    saveBtn.disabled = false;
  }
}


function collectMovieQualities() {
  const qualities = [];
  const container = document.getElementById('movie-qualities-container');
  
  if (!container) return qualities;
  
  container.querySelectorAll('.quality-item').forEach((qualityItem, index) => {
    const quality = {
      type: qualityItem.querySelector(`input[name="quality_type_${index}"]`)?.value || '',
      size: qualityItem.querySelector(`input[name="quality_size_${index}"]`)?.value || '',
      audio: qualityItem.querySelector(`input[name="quality_audio_${index}"]`)?.value || '',
      video_codec: qualityItem.querySelector(`input[name="quality_codec_${index}"]`)?.value || '',
      file_type: qualityItem.querySelector(`input[name="quality_file_type_${index}"]`)?.value || '',
      subtitle: qualityItem.querySelector(`input[name="quality_subtitle_${index}"]`)?.value || '',
      msg_id: parseInt(qualityItem.querySelector(`input[name="quality_msg_id_${index}"]`)?.value) || null,
      chat_id: parseInt(qualityItem.querySelector(`input[name="quality_chat_id_${index}"]`)?.value) || null,
      file_hash: qualityItem.querySelector(`input[name="quality_file_hash_${index}"]`)?.value || ''
    };
    
    
    if (quality.type) {
      
      Object.keys(quality).forEach(key => {
        if (quality[key] === null || quality[key] === '') {
          delete quality[key];
        }
      });
      qualities.push(quality);
    }
  });
  
  return qualities;
}


function collectShowSeasons() {
  const seasons = [];
  const container = document.getElementById('seasons-container');
  
  if (!container) return seasons;
  
  container.querySelectorAll('.season-item').forEach((seasonItem, seasonIndex) => {
    const seasonNumber = parseInt(seasonItem.querySelector(`input[name="season_number_${seasonIndex}"]`)?.value) || (seasonIndex + 1);
    
    const episodes = [];
    const episodesContainer = seasonItem.querySelector(`#episodes-container-${seasonIndex}`);
    
    if (episodesContainer) {
      episodesContainer.querySelectorAll('.episode-item').forEach((episodeItem, episodeIndex) => {
        const episode = {
          episode_number: parseInt(episodeItem.querySelector(`input[name="episode_number_${seasonIndex}_${episodeIndex}"]`)?.value) || (episodeIndex + 1),
          name: episodeItem.querySelector(`input[name="episode_name_${seasonIndex}_${episodeIndex}"]`)?.value || '',
          air_date: episodeItem.querySelector(`input[name="episode_air_date_${seasonIndex}_${episodeIndex}"]`)?.value || '',
          still_path: episodeItem.querySelector(`input[name="episode_still_path_${seasonIndex}_${episodeIndex}"]`)?.value || '',
          overview: episodeItem.querySelector(`textarea[name="episode_overview_${seasonIndex}_${episodeIndex}"]`)?.value || ''
        };
        
        
        const episodeQualities = [];
        const qualitiesContainer = episodeItem.querySelector(`#episode-qualities-${seasonIndex}-${episodeIndex}`);
        
        if (qualitiesContainer) {
          qualitiesContainer.querySelectorAll('.quality-item').forEach((qualityItem, qualityIndex) => {
            const quality = {
              type: qualityItem.querySelector(`input[name="ep_quality_type_${seasonIndex}_${episodeIndex}_${qualityIndex}"]`)?.value || '',
              size: qualityItem.querySelector(`input[name="ep_quality_size_${seasonIndex}_${episodeIndex}_${qualityIndex}"]`)?.value || '',
              audio: qualityItem.querySelector(`input[name="ep_quality_audio_${seasonIndex}_${episodeIndex}_${qualityIndex}"]`)?.value || '',
              video_codec: qualityItem.querySelector(`input[name="ep_quality_codec_${seasonIndex}_${episodeIndex}_${qualityIndex}"]`)?.value || '',
              file_type: qualityItem.querySelector(`input[name="ep_quality_file_type_${seasonIndex}_${episodeIndex}_${qualityIndex}"]`)?.value || '',
              subtitle: qualityItem.querySelector(`input[name="ep_quality_subtitle_${seasonIndex}_${episodeIndex}_${qualityIndex}"]`)?.value || '',
              runtime: parseInt(qualityItem.querySelector(`input[name="ep_quality_runtime_${seasonIndex}_${episodeIndex}_${qualityIndex}"]`)?.value) || null,
              msg_id: parseInt(qualityItem.querySelector(`input[name="ep_quality_msg_id_${seasonIndex}_${episodeIndex}_${qualityIndex}"]`)?.value) || null,
              chat_id: parseInt(qualityItem.querySelector(`input[name="ep_quality_chat_id_${seasonIndex}_${episodeIndex}_${qualityIndex}"]`)?.value) || null,
              file_hash: qualityItem.querySelector(`input[name="ep_quality_file_hash_${seasonIndex}_${episodeIndex}_${qualityIndex}"]`)?.value || ''
            };
            
            
            if (quality.type) {
              
              Object.keys(quality).forEach(key => {
                if (quality[key] === null || quality[key] === '') {
                  delete quality[key];
                }
              });
              episodeQualities.push(quality);
            }
          });
        }
        
        episode.quality = episodeQualities;
        
        
        Object.keys(episode).forEach(key => {
          if (episode[key] === '' || (Array.isArray(episode[key]) && episode[key].length === 0)) {
            delete episode[key];
          }
        });
        
        episodes.push(episode);
      });
    }
    
    const season = {
      season_number: seasonNumber,
      episodes: episodes
    };
    
    seasons.push(season);
  });
  
  return seasons;
}


function removeSeason(seasonIndex) {
  const seasonItem = document.querySelector(`[data-season="${seasonIndex}"]`);
  if (seasonItem) {
    seasonItem.remove();
  }
}

function removeEpisode(seasonIndex, episodeIndex) {
  const episodeItem = document.querySelector(`[data-episode="${episodeIndex}"]`);
  if (episodeItem) {
    episodeItem.remove();
  }
}

function removeEpisodeQuality(seasonIndex, episodeIndex, qualityIndex) {
  const qualityItem = document.querySelector(`[data-quality="${qualityIndex}"]`);
  if (qualityItem) {
    qualityItem.remove();
  }
}


document.getElementById('add-movie-quality-btn').addEventListener('click', function() {
  addMovieQualityItem();
});

document.getElementById('add-season-btn').addEventListener('click', function() {
  addSeasonItem();
});
