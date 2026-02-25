import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { Container, ListGroup, Button } from 'react-bootstrap';

const History = () => {
  const [documents, setDocuments] = useState([]);

  useEffect(() => {
    const fetchData = async () => {
      const result = await axios('/api/history/');
      setDocuments(result.data);
    };
    fetchData();
  }, []);

  return (
    <Container>
      <h1>Historique des analyses</h1>
      <ListGroup>
        {documents.map(doc => (
          <ListGroup.Item key={doc.id}>
            {doc.name} - {doc.upload_date}
            <Button variant="link" onClick={() => window.location = `/results/${doc.id}`}>Voir les détails</Button>
            <Button variant="link" onClick={() => window.location = `/api/report/${doc.id}`}>Télécharger le rapport</Button>
          </ListGroup.Item>
        ))}
      </ListGroup>
    </Container>
  );
}

export default History;
