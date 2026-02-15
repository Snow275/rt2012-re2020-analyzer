import React, { useState } from 'react';
import axios from 'axios';
import { Container, Form, Button } from 'react-bootstrap';

const Import = () => {
  const [file, setFile] = useState(null);

  const handleFileChange = (e) => {
    setFile(e.target.files[0]);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    const formData = new FormData();
    formData.append('file', file);

    try {
      await axios.post('/api/upload/', formData);
      alert('Document importé avec succès.');
    } catch (error) {
      console.error('Erreur lors de l\'importation du document', error);
    }
  };

  return (
    <Container>
      <h1>Importer un document technique</h1>
      <Form onSubmit={handleSubmit}>
        <Form.Group>
          <Form.File label="Choisir un fichier" onChange={handleFileChange} />
        </Form.Group>
        <Button type="submit">Télécharger</Button>
      </Form>
    </Container>
  );
}

export default Import;
