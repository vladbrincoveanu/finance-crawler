import React from 'react';
import { Link as RouterLink, Outlet } from 'react-router-dom';
import {
  Box,
  Flex,
  Text,
  IconButton,
  Button,
  Stack,
  Collapse,
  Link,
  useBreakpointValue,
  useDisclosure,
  Container,
} from '@chakra-ui/react';
import { HamburgerIcon, CloseIcon } from '@chakra-ui/icons';

const Layout: React.FC = () => {
  const { isOpen, onToggle } = useDisclosure();

  // Define common theme values
  const bgColor = 'rgba(7, 11, 20, 0.88)';
  const textColor = 'whiteAlpha.800';
  const borderColor = 'whiteAlpha.200';

  return (
    <Box minH="100vh">
      <Box
        bg={bgColor}
        color={textColor}
        borderBottom={1}
        borderStyle="solid"
        borderColor={borderColor}
        position="sticky"
        top={0}
        zIndex={10}
        backdropFilter="blur(18px)"
      >
        <Flex
          bg={bgColor}
          color={textColor}
          minH="60px"
          py={{ base: 2 }}
          px={{ base: 4 }}
          align="center"
          maxW="1400px"
          mx="auto"
        >
          <Flex
            flex={{ base: 1, xl: 'auto' }}
            ml={{ base: -2 }}
            display={{ base: 'flex', xl: 'none' }}
          >
            <IconButton
              onClick={onToggle}
              icon={isOpen ? <CloseIcon w={3} h={3} /> : <HamburgerIcon w={5} h={5} />}
              variant="ghost"
              aria-label="Toggle Navigation"
            />
          </Flex>
          <Flex flex={{ base: 1 }} justify={{ base: 'center', xl: 'start' }}>
            <Text
              textAlign={useBreakpointValue({ base: 'center', xl: 'left' })}
              fontFamily="heading"
              color="white"
              fontWeight="bold"
              fontSize="xl"
              as={RouterLink}
              to="/"
            >
              VIC / FIELD NOTES
            </Text>

            <Flex display={{ base: 'none', xl: 'flex' }} ml={10}>
              <DesktopNav />
            </Flex>
          </Flex>

          <Stack
            flex={{ base: 1, xl: 0 }}
            justify="flex-end"
            direction="row"
            spacing={6}
          >
            <Button
              as={RouterLink}
              fontSize="sm"
              fontWeight={400}
              variant="link"
              to="/about"
            >
              About
            </Button>
          </Stack>
        </Flex>

        <Collapse in={isOpen} animateOpacity>
          <MobileNav />
        </Collapse>
      </Box>

      <Container maxW="1400px" pt={{ base: 8, md: 12 }} pb={20}>
        <Outlet />
      </Container>

      <Box
        as="footer"
        bg="rgba(255,255,255,0.025)"
        color="whiteAlpha.600"
        mt="auto"
        py={6}
        borderTop={1}
        borderStyle="solid"
        borderColor={borderColor}
      >
        <Container
          as={Stack}
          maxW="1400px"
          py={4}
          direction={{ base: 'column', md: 'row' }}
          spacing={4}
          justify={{ base: 'center', md: 'space-between' }}
          align={{ base: 'center', md: 'center' }}
        >
          <Text>© {new Date().getFullYear()} VIC Analytics Dashboard. Not affiliated with ValueInvestorsClub.com</Text>
        </Container>
      </Box>
    </Box>
  );
};

const DesktopNav = () => {
  const linkColor = 'whiteAlpha.700';
  const linkHoverColor = 'amber.200';

  return (
    <Stack direction="row" spacing={4}>
      {NAV_ITEMS.map((navItem) => (
        <Box key={navItem.label}>
          <Link
            p={2}
            as={RouterLink}
            to={navItem.href ?? '#'}
            fontSize="sm"
            fontWeight={500}
            color={linkColor}
            _hover={{
              textDecoration: 'none',
              color: linkHoverColor,
            }}
          >
            {navItem.label}
          </Link>
        </Box>
      ))}
    </Stack>
  );
};

const MobileNav = () => {
  return (
    <Stack
      bg="ink.900"
      p={4}
      display={{ xl: 'none' }}
    >
      {NAV_ITEMS.map((navItem) => (
        <MobileNavItem key={navItem.label} {...navItem} />
      ))}
    </Stack>
  );
};

const MobileNavItem = ({ label, href }: NavItem) => {
  return (
    <Stack spacing={4}>
      <Flex
        py={2}
        as={RouterLink}
        to={href ?? '#'}
        justify="space-between"
        align="center"
        _hover={{
          textDecoration: 'none',
        }}
      >
        <Text
          fontWeight={600}
          color="whiteAlpha.800"
        >
          {label}
        </Text>
      </Flex>
    </Stack>
  );
};

interface NavItem {
  label: string;
  href?: string;
}

const NAV_ITEMS: Array<NavItem> = [
  {
    label: 'Ideas',
    href: '/ideas',
  },
  {
    label: 'Articles',
    href: '/articles',
  },
  {
    label: 'Companies',
    href: '/companies',
  },
  {
    label: 'Users',
    href: '/users',
  },
  {
    label: 'Holdings',
    href: '/holdings',
  },
  {
    label: 'Dataroma',
    href: '/holdings/dataroma',
  },
  {
    label: 'HedgeFollow',
    href: '/holdings/hedgefollow',
  },
];

export default Layout;
