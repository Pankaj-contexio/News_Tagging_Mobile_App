import React, { useState } from 'react';
import { View, Text, Button, TextInput, StyleSheet, ScrollView } from 'react-native';
import { useDispatch } from 'react-redux';
import { addTag } from '../store/newsSlice';

export default function NewsDetailScreen({ route }) {
  const { item } = route.params;
  const [tag, setTag] = useState('');
  const dispatch = useDispatch();

  const handleAddTag = () => {
    if (tag.trim()) {
      dispatch(addTag({ newsId: item.id, tag }));
      setTag('');
    }
  };

  return (
    <ScrollView contentContainerStyle={styles.container}>
      <Text style={styles.title}>{item.title}</Text>
      <Text style={styles.content}>{item.content}</Text>
      <View style={styles.tagRow}>
        <TextInput
          style={styles.input}
          placeholder="Add tag"
          value={tag}
          onChangeText={setTag}
        />
        <Button title="Add" onPress={handleAddTag} />
      </View>
      <Text style={styles.tagTitle}>Tags:</Text>
      {item.tags && item.tags.map((t, idx) => (
        <Text key={idx} style={styles.tag}>{t}</Text>
      ))}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    padding: 16,
  },
  title: {
    fontSize: 20,
    fontWeight: 'bold',
    marginBottom: 10,
  },
  content: {
    marginBottom: 20,
  },
  tagRow: {
    flexDirection: 'row',
    marginBottom: 10,
  },
  input: {
    flex: 1,
    borderWidth: 1,
    borderColor: '#ccc',
    marginRight: 10,
    padding: 5,
    borderRadius: 5,
  },
  tagTitle: {
    fontWeight: 'bold',
    marginTop: 10,
  },
  tag: {
    backgroundColor: '#eee',
    padding: 5,
    marginTop: 5,
    borderRadius: 5,
  },
});
