import React, { useEffect, useState } from 'react';
import { Routes, Route } from 'react-router-dom';
import { Box, Spinner, Center, Alert, AlertIcon, AlertTitle, AlertDescription } from '@chakra-ui/react';
import { healthApi } from './api/apiService';

// Layout
import Layout from './components/Layout';

// Pages
import HomePage from './pages/HomePage';
import IdeasPage from './pages/IdeasPage';
import IdeaDetailPage from './pages/IdeaDetailPage';
import ArticlesPage from './pages/ArticlesPage';
import ArticleDetailPage from './pages/ArticleDetailPage';
import CompaniesPage from './pages/CompaniesPage';
import UsersPage from './pages/UsersPage';
import HoldingsPage from './pages/HoldingsPage';
import SourceHoldingsPage from './pages/SourceHoldingsPage';
import IdentityReviewPage from './pages/IdentityReviewPage';
import QuarantineReviewPage from './pages/QuarantineReviewPage';
import AboutPage from './pages/AboutPage';

function App() {
  const [apiStatus, setApiStatus] = useState<'loading' | 'available' | 'error'>('loading');

  useEffect(() => {
    const checkApiStatus = async () => {
      try {
        await healthApi.check();
        setApiStatus('available');
      } catch (error) {
        console.error('API health check failed:', error);
        setApiStatus('error');
      }
    };

    checkApiStatus();
  }, []);

  if (apiStatus === 'loading') {
    return (
      <Center h="100vh">
        <Spinner size="xl" />
        <Box ml={4}>Connecting to API...</Box>
      </Center>
    );
  }

  if (apiStatus === 'error') {
    return (
      <Center h="100vh">
        <Alert
          status="error"
          variant="subtle"
          flexDirection="column"
          alignItems="center"
          justifyContent="center"
          textAlign="center"
          height="auto"
          maxW="600px"
          py={8}
          borderRadius="md"
        >
          <AlertIcon boxSize="40px" mr={0} />
          <AlertTitle mt={4} mb={3} fontSize="xl">
            API Connection Error
          </AlertTitle>
          <AlertDescription maxWidth="sm">
            Unable to connect to the API. Please ensure the API server is running at
            http://localhost:8010 and refresh the page.
          </AlertDescription>
        </Alert>
      </Center>
    );
  }

  return (
    <Routes>
      <Route path="/" element={<Layout />}>
        <Route index element={<HomePage />} />
        <Route path="ideas" element={<IdeasPage />} />
        <Route path="ideas/:id" element={<IdeaDetailPage />} />
        <Route path="articles" element={<ArticlesPage />} />
        <Route path="articles/:id" element={<ArticleDetailPage />} />
        <Route path="companies" element={<CompaniesPage />} />
        <Route path="users" element={<UsersPage />} />
        <Route path="holdings" element={<HoldingsPage />} />
        <Route path="holdings/dataroma" element={<SourceHoldingsPage source="dataroma" />} />
        <Route path="holdings/hedgefollow" element={<SourceHoldingsPage source="hedgefollow" />} />
        <Route path="review/identity" element={<IdentityReviewPage />} />
        <Route path="review/quarantine" element={<QuarantineReviewPage />} />
        <Route path="about" element={<AboutPage />} />
      </Route>
    </Routes>
  );
}

export default App;
