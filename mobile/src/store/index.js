import { configureStore } from '@reduxjs/toolkit';
import authReducer from './authSlice';
import newsReducer from './newsSlice';
import dashboardReducer from './dashboardSlice';

const store = configureStore({
  reducer: {
    auth: authReducer,
    news: newsReducer,
    dashboard: dashboardReducer,
  },
});

export default store;
