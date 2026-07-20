import axios from "axios";

// Create configured Axios instance pointing to the API proxy
export const api = axios.create({
  baseURL: "/api/v1",
  headers: {
    "Content-Type": "application/json",
  },
});
