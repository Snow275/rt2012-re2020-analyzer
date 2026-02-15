import React from 'react';
import { Container, Form, Button } from 'react-bootstrap';

const Settings = () => {
  return (
    <Container>
      <h1>Paramètres</h1>
      <Form>
        <Form.Group>
          <Form.Label>Langue :</Form.Label>
          <Form.Control as="select">
            <option value="fr">Français</option>
            <option value="en">Anglais</option>
          </Form.Control>
        </Form.Group>
        <Form.Group>
          <Form.Check type="checkbox" label="Notifications par email" />
        </Form.Group>
        <Button type="submit">Enregistrer les modifications</Button>
      </Form>
    </Container>
  );
}

export default Settings;
