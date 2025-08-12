import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
import api from '../api';
import { saveToken, clearToken, getToken } from '../utils/storage';

export const login = createAsyncThunk('auth/login', async (credentials) => {
  const response = await api.post('/login', credentials);
  const token = response.data.token;
  await saveToken(token);
  return { token };
});

export const loadToken = createAsyncThunk('auth/loadToken', async () => {
  const token = await getToken();
  return { token };
});

const authSlice = createSlice({
  name: 'auth',
  initialState: {
    token: null,
    status: 'idle',
    error: null,
  },
  reducers: {
    logout: (state) => {
      state.token = null;
      clearToken();
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(login.pending, (state) => {
        state.status = 'loading';
      })
      .addCase(login.fulfilled, (state, action) => {
        state.status = 'succeeded';
        state.token = action.payload.token;
      })
      .addCase(login.rejected, (state, action) => {
        state.status = 'failed';
        state.error = action.error.message;
      })
      .addCase(loadToken.fulfilled, (state, action) => {
        state.token = action.payload.token;
      });
  },
});

export const { logout } = authSlice.actions;
export default authSlice.reducer;
