import React from 'react';
import { Container, Jumbotron } from 'react-bootstrap';

const Home = () => {
  return (
    <Container>
      <Jumbotron>
        <h1>Bienvenue sur l'outil de conformité RE2020</h1>
        <p>Utilisez le menu pour naviguer entre les différentes sections.</p>
      </Jumbotron>
    </Container>
  );
}

export default Home;
