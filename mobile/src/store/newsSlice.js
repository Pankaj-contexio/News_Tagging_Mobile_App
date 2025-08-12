import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
import api from '../api';
import { saveNewsCache, getNewsCache } from '../utils/storage';

export const fetchNews = createAsyncThunk(
  'news/fetchNews',
  async ({ page = 1, search = '', filters = {} }) => {
    const params = { page, search, ...filters };
    const response = await api.get('/news', { params });
    await saveNewsCache(response.data.items);
    return response.data;
  }
);

export const loadCachedNews = createAsyncThunk('news/loadCached', async () => {
  const items = await getNewsCache();
  return items;
});

export const addTag = createAsyncThunk(
  'news/addTag',
  async ({ newsId, tag }) => {
    const response = await api.post(`/news/${newsId}/tags`, { tag });
    return { newsId, tag: response.data.tag };
  }
);

const newsSlice = createSlice({
  name: 'news',
  initialState: {
    items: [],
    page: 1,
    totalPages: 1,
    status: 'idle',
    error: null,
  },
  reducers: {},
  extraReducers: (builder) => {
    builder
      .addCase(fetchNews.pending, (state) => {
        state.status = 'loading';
      })
      .addCase(fetchNews.fulfilled, (state, action) => {
        state.status = 'succeeded';
        state.items = action.payload.items;
        state.page = action.payload.page;
        state.totalPages = action.payload.total_pages;
      })
      .addCase(fetchNews.rejected, (state, action) => {
        state.status = 'failed';
        state.error = action.error.message;
      })
      .addCase(loadCachedNews.fulfilled, (state, action) => {
        state.items = action.payload;
      })
      .addCase(addTag.fulfilled, (state, action) => {
        const item = state.items.find((n) => n.id === action.payload.newsId);
        if (item) {
          item.tags.push(action.payload.tag);
        }
      });
  },
});

export default newsSlice.reducer;
