import React, { useEffect, useState } from 'react';
import { View, Text, FlatList, TextInput, Button, StyleSheet } from 'react-native';
import { useDispatch, useSelector } from 'react-redux';
import { fetchNews, loadCachedNews } from '../store/newsSlice';
import { useNavigation } from '@react-navigation/native';
import NewsItem from '../components/NewsItem';

export default function NewsListScreen() {
  const dispatch = useDispatch();
  const navigation = useNavigation();
  const { items, page, totalPages, status } = useSelector((state) => state.news);
  const [search, setSearch] = useState('');

  useEffect(() => {
    dispatch(loadCachedNews());
    dispatch(fetchNews({ page: 1 }));
  }, [dispatch]);

  const loadMore = () => {
    if (page < totalPages) {
      dispatch(fetchNews({ page: page + 1, search }));
    }
  };

  const handleSearch = () => {
    dispatch(fetchNews({ page: 1, search }));
  };

  const renderItem = ({ item }) => (
    <NewsItem item={item} onPress={() => navigation.navigate('NewsDetail', { item })} />
  );

  return (
    <View style={styles.container}>
      <View style={styles.searchRow}>
        <TextInput style={styles.searchInput} placeholder="Search" value={search} onChangeText={setSearch} />
        <Button title="Go" onPress={handleSearch} />
      </View>
      {status === 'loading' && <Text>Loading...</Text>}
      <FlatList
        data={items}
        keyExtractor={(item) => item.id.toString()}
        renderItem={renderItem}
        onEndReached={loadMore}
        onEndReachedThreshold={0.5}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    padding: 10,
  },
  searchRow: {
    flexDirection: 'row',
    marginBottom: 10,
  },
  searchInput: {
    flex: 1,
    borderWidth: 1,
    borderColor: '#ccc',
    marginRight: 10,
    padding: 5,
    borderRadius: 5,
  },
});
