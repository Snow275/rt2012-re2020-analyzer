import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { Container, Table } from 'react-bootstrap';

const Results = () => {
  const [documents, setDocuments] = useState([]);

  useEffect(() => {
    const fetchData = async () => {
      const result = await axios('/api/results/');
      setDocuments(result.data);
    };
    fetchData();
  }, []);

  return (
    <Container>
      <h1>Résultats de l'analyse</h1>
      <Table striped bordered hover>
        <thead>
          <tr>
            <th>Document</th>
            <th>Critère</th>
            <th>Valeur</th>
            <th>Exigence</th>
            <th>Conformité</th>
          </tr>
        </thead>
        <tbody>
          {documents.map(doc => (
            <tr key={doc.id}>
              <td>{doc.name}</td>
              <td>{doc.criteria}</td>
              <td>{doc.value}</td>
              <td>{doc.requirement}</td>
              <td style={{color: doc.compliance ? 'green' : 'red'}}>
                {doc.compliance ? 'Conforme' : 'Non conforme'}
              </td>
            </tr>
          ))}
        </tbody>
      </Table>
    </Container>
  );
}

export default Results;
