import React, { useEffect, useState } from 'react';
import {
  Button,
  Drawer,
  DrawerBody,
  DrawerCloseButton,
  DrawerContent,
  DrawerFooter,
  DrawerHeader,
  DrawerOverlay,
  FormControl,
  FormLabel,
  Input,
  Select,
  Stack,
} from '@chakra-ui/react';
import { ListParams } from '../types/api';
import {
  booleanSelectionToFilter,
  BooleanSelection,
  PERFORMANCE_PERIOD_LABELS,
  positionSelectionToFilter,
  PositionSelection,
} from '../pages/ideasFilters';

interface IdeasFilterDrawerProps {
  isOpen: boolean;
  filters: ListParams;
  onClose: () => void;
  onApply: (filters: ListParams) => void;
  onReset: () => void;
}

const PERFORMANCE_PERIODS = Object.keys(PERFORMANCE_PERIOD_LABELS);

const IdeasFilterDrawer: React.FC<IdeasFilterDrawerProps> = ({
  isOpen,
  filters,
  onClose,
  onApply,
  onReset,
}) => {
  const [draftFilters, setDraftFilters] = useState<ListParams>(filters);

  useEffect(() => {
    if (isOpen) {
      setDraftFilters(filters);
    }
  }, [filters, isOpen]);

  const updateDraft = (field: keyof ListParams, value: unknown) => {
    setDraftFilters(previous => {
      const next = { ...previous };
      if (value === undefined || value === '') {
        delete next[field];
      } else {
        (next as Record<string, unknown>)[field] = value;
      }
      return next;
    });
  };

  const handlePositionChange = (value: PositionSelection) => {
    updateDraft('is_short', positionSelectionToFilter(value));
  };

  const handleBooleanChange = (field: 'is_contest_winner' | 'has_performance', value: BooleanSelection) => {
    updateDraft(field, booleanSelectionToFilter(value));
  };

  const handleReset = () => {
    onReset();
    onClose();
  };

  return (
    <Drawer isOpen={isOpen} placement="right" onClose={onClose} size="sm">
      <DrawerOverlay />
      <DrawerContent
        bg="ink.900"
        color="white"
        maxW="100vw"
        w={{ base: '100vw', md: '420px' }}
      >
        <DrawerCloseButton aria-label="Close" />
        <DrawerHeader borderBottomWidth="1px" borderColor="whiteAlpha.200">
          Filters
        </DrawerHeader>

        <DrawerBody py={6}>
          <Stack spacing={5}>
            <FormControl>
              <FormLabel htmlFor="ideas-position-filter">Position</FormLabel>
              <Select
                id="ideas-position-filter"
                aria-label="Position"
                value={
                  draftFilters.is_short === undefined
                    ? 'all'
                    : draftFilters.is_short
                      ? 'short'
                      : 'long'
                }
                onChange={event => handlePositionChange(event.target.value as PositionSelection)}
              >
                <option value="all">All positions</option>
                <option value="long">Long only</option>
                <option value="short">Short only</option>
              </Select>
            </FormControl>

            <FormControl>
              <FormLabel htmlFor="ideas-winner-filter">Contest winner</FormLabel>
              <Select
                id="ideas-winner-filter"
                aria-label="Contest winner"
                value={
                  draftFilters.is_contest_winner === undefined
                    ? 'all'
                    : draftFilters.is_contest_winner
                      ? 'yes'
                      : 'no'
                }
                onChange={event => handleBooleanChange(
                  'is_contest_winner',
                  event.target.value as BooleanSelection,
                )}
              >
                <option value="all">All ideas</option>
                <option value="yes">Winners only</option>
                <option value="no">Non-winners only</option>
              </Select>
            </FormControl>

            <FormControl>
              <FormLabel htmlFor="ideas-performance-filter">Performance status</FormLabel>
              <Select
                id="ideas-performance-filter"
                aria-label="Performance status"
                value={
                  draftFilters.has_performance === undefined
                    ? 'all'
                    : draftFilters.has_performance
                      ? 'yes'
                      : 'no'
                }
                onChange={event => handleBooleanChange(
                  'has_performance',
                  event.target.value as BooleanSelection,
                )}
              >
                <option value="all">Any status</option>
                <option value="yes">Performance tracked</option>
                <option value="no">Performance untracked</option>
              </Select>
            </FormControl>

            <Stack direction={{ base: 'column', md: 'row' }} spacing={3}>
              <FormControl>
                <FormLabel htmlFor="ideas-min-performance">Min performance (%)</FormLabel>
                <Input
                  id="ideas-min-performance"
                  aria-label="Min performance"
                  type="number"
                  value={draftFilters.min_performance ?? ''}
                  onChange={event => updateDraft(
                    'min_performance',
                    event.target.value === '' ? undefined : Number(event.target.value),
                  )}
                />
              </FormControl>
              <FormControl>
                <FormLabel htmlFor="ideas-max-performance">Max performance (%)</FormLabel>
                <Input
                  id="ideas-max-performance"
                  aria-label="Max performance"
                  type="number"
                  value={draftFilters.max_performance ?? ''}
                  onChange={event => updateDraft(
                    'max_performance',
                    event.target.value === '' ? undefined : Number(event.target.value),
                  )}
                />
              </FormControl>
            </Stack>

            <FormControl>
              <FormLabel htmlFor="ideas-performance-period">Performance period</FormLabel>
              <Select
                id="ideas-performance-period"
                aria-label="Performance period"
                value={draftFilters.performance_period || 'one_year_perf'}
                onChange={event => updateDraft('performance_period', event.target.value)}
              >
                {PERFORMANCE_PERIODS.map(period => (
                  <option key={period} value={period}>
                    {PERFORMANCE_PERIOD_LABELS[period]}
                  </option>
                ))}
              </Select>
            </FormControl>
          </Stack>
        </DrawerBody>

        <DrawerFooter gap={3} borderTopWidth="1px" borderColor="whiteAlpha.200">
          <Button variant="ghost" onClick={handleReset} minW="90px">
            Reset
          </Button>
          <Button colorScheme="orange" flex={1} onClick={() => {
            onApply({ ...draftFilters, skip: 0 });
            onClose();
          }}>
            Apply filters
          </Button>
        </DrawerFooter>
      </DrawerContent>
    </Drawer>
  );
};

export default IdeasFilterDrawer;
