import AsyncStorage from '@react-native-async-storage/async-storage';

export const saveToken = async (token) => {
  try {
    await AsyncStorage.setItem('token', token);
  } catch (e) {
    console.error('Error saving token', e);
  }
};

export const getToken = async () => {
  try {
    return await AsyncStorage.getItem('token');
  } catch (e) {
    console.error('Error getting token', e);
    return null;
  }
};

export const clearToken = async () => {
  try {
    await AsyncStorage.removeItem('token');
  } catch (e) {
    console.error('Error clearing token', e);
  }
};

export const saveNewsCache = async (news) => {
  try {
    await AsyncStorage.setItem('news_cache', JSON.stringify(news));
  } catch (e) {
    console.error('Error saving news cache', e);
  }
};

export const getNewsCache = async () => {
  try {
    const news = await AsyncStorage.getItem('news_cache');
    return news ? JSON.parse(news) : [];
  } catch (e) {
    console.error('Error getting news cache', e);
    return [];
  }
};
