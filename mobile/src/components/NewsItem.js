import React from 'react';
import { TouchableOpacity, Text, StyleSheet } from 'react-native';

export default function NewsItem({ item, onPress }) {
  return (
    <TouchableOpacity style={styles.item} onPress={onPress}>
      <Text style={styles.title}>{item.title}</Text>
      <Text numberOfLines={2}>{item.summary}</Text>
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  item: {
    padding: 10,
    borderBottomWidth: 1,
    borderBottomColor: '#eee',
  },
  title: {
    fontWeight: 'bold',
  },
});
